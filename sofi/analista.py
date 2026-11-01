"""Analista de cartera de Sofi/ANP. Trabaja sobre el snapshot que envía la interfaz (stateless)."""
import math
def _rets(h): return [math.log(b/a) for a,b in zip(h,h[1:]) if a>0 and b>0]
def _sd(x):
    if len(x)<2: return 0.0
    m=sum(x)/len(x); return math.sqrt(sum((v-m)**2 for v in x)/(len(x)-1))
def _rsi(h):
    if len(h)<15: return None
    g=l=0.0
    for a,b in zip(h[-15:],h[-14:]):
        d=b-a; g+=max(d,0); l+=max(-d,0)
    return 100-100/(1+g/l) if l else 100.0
def _f(n,d=2): return f"{n:,.{d}f}"
def _act(c): return [a for a in c.get("a",[]) if a.get("q",0)>0 and a.get("p",0)>0]
def resumen(c):
    A=_act(c)
    if not A: return "Tu cartera está vacía. Puedes decir, por ejemplo: agrega 2 SOL a 150 usd."
    fx=c.get("fx",18.7); mxw=c.get("maxW",.3); T=sum(a["q"]*a["p"] for a in A); C=sum(a["q"]*a["c"] for a in A) or 1
    W={a["s"]:a["q"]*a["p"]/T for a in A}; top=max(W,key=W.get); ef=1/sum(w*w for w in W.values())
    out=[f"Valor: ${_f(T)} MXN (≈US${_f(T/fx)}), PNL no realizado {(T/C-1)*100:+.1f}%.",
         f"Mayor posición: {top} con {W[top]*100:.1f}% (límite {mxw*100:.0f}%). Diversificación efectiva: {ef:.1f} activos equivalentes."]
    L=min([len(a.get("h",[])) for a in A]+[10**9])
    if 30<L<10**9:
        ps=[sum(a["q"]*a["h"][-L+i]*fx for a in A) for i in range(L)]; r=_rets(ps); vol=_sd(r)*math.sqrt(365); pk=dd=0
        for v in ps: pk=max(pk,v); dd=min(dd,v/pk-1)
        mu=sum(r)/len(r); var=max(0,-(mu*30-1.645*_sd(r)*math.sqrt(30)))
        out.append(f"Volatilidad anual {vol*100:.0f}%, drawdown máximo {dd*100:.1f}%, VaR95 mensual {var*100:.1f}%.")
    al=[]
    for a in A:
        p=a["p"]/a["c"]-1; R=_rsi(a.get("h",[])); s=a["s"]
        if W[s]>mxw: al.append(f"{s}: peso alto, recortar")
        elif p>=c.get("tp",.15): al.append(f"{s}: toma parcial (+{p*100:.0f}%)")
        elif p<=-.3: al.append(f"{s}: revisar tesis ({p*100:.0f}%)")
        if R and R>72: al.append(f"{s}: RSI {R:.0f}, sobrecompra")
        if R and R<28: al.append(f"{s}: RSI {R:.0f}, sobreventa")
    out.append("Alertas: "+("; ".join(al) if al else "ninguna por ahora."))
    meta=c.get("meta",1e6); out.append(f"Progreso a la meta de US${_f(meta,0)}: {T/fx/meta*100:.4f}%.")
    return "\n".join(out)
def rebalanceo(c):
    A=_act(c)
    if not A: return "No hay activos que rebalancear."
    fx=c.get("fx",18.7); mx=c.get("maxW",.3); mn=c.get("minW",.05); T=sum(a["q"]*a["p"] for a in A); ap=c.get("ap",100)*fx
    out=[f"Rebalanceo sugerido (máx {mx*100:.0f}%, mín {mn*100:.0f}% por activo):"]
    ex=[(a["s"],a["q"]*a["p"]-mx*T,(a["q"]*a["p"]-mx*T)/a["p"]) for a in A if a["q"]*a["p"]>mx*T]
    for s,m,q in ex: out.append(f"• Recortar {s}: ≈${_f(m)} MXN ({q:,.6g} unidades) para quedar en el máximo.")
    bajos=sorted([a for a in A if a["q"]*a["p"]/T<mn],key=lambda a:a["q"]*a["p"])
    if bajos: out.append(f"• Reforzar con tu aporte de ≈${_f(ap)} MXN/mes: "+", ".join(a["s"] for a in bajos)+".")
    if not ex and not bajos: out.append("• Tus pesos ya están dentro de los límites.")
    out.append("Son cálculos mecánicos con tus reglas, sin considerar comisiones ni impuestos; no son asesoría financiera.")
    return "\n".join(out)
