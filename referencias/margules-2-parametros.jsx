import React, { useState, useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from 'recharts';

const C = {
  g1: '#2563eb',    // componente 1 — azul
  g2: '#ea580c',    // componente 2 — laranja
  gE: '#7c3aed',    // Gibbs em excesso — violeta
  ghost: '#c4b5fd', // Margules-1 de referência
  ideal: '#94a3b8',
  grid: '#eef2f6',
  ink: '#1e293b',
  muted: '#64748b',
  ok: '#10b981',
};

// Pilha de fontes monoespaçadas com cobertura de grego (γ, Λ, τ, α).
const MONO = 'ui-monospace, SFMono-Regular, Menlo, "DejaVu Sans Mono", Consolas, monospace';

const fmt = (v, d = 2) => Number(v).toFixed(d);

function Card({ title, hint, children }) {
  return (
    <div style={{
      background: '#fff', border: '1px solid #e7ecf2', borderRadius: 14,
      padding: '14px 12px 6px', boxShadow: '0 1px 2px rgba(15,23,42,0.03)',
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', padding: '0 4px 8px' }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: C.ink }}>{title}</span>
        <span style={{ fontSize: 11, color: C.muted, fontFamily: MONO }}>{hint}</span>
      </div>
      {children}
    </div>
  );
}

function TT({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div style={{
      background: '#0f172a', color: '#e2e8f0', borderRadius: 8, padding: '8px 10px',
      fontSize: 12, fontFamily: MONO, lineHeight: 1.5,
    }}>
      <div style={{ color: '#94a3b8', marginBottom: 2 }}>x₁ = {fmt(label, 2)}</div>
      {payload.map((p) => (
        <div key={p.name} style={{ color: p.color }}>{p.name} = {fmt(p.value, 3)}</div>
      ))}
    </div>
  );
}

function Slider({ label, color, value, onChange }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 13, fontWeight: 700, fontFamily: MONO, color }}>{label}</span>
        <span style={{ fontSize: 22, fontWeight: 800, fontFamily: MONO, letterSpacing: -0.5 }}>
          {value >= 0 ? '+' : ''}{fmt(value, 2)}
        </span>
      </div>
      <input
        type="range" min={-3} max={3} step={0.05} value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        style={{ width: '100%', accentColor: color, height: 6, cursor: 'pointer' }}
      />
    </div>
  );
}

export default function App() {
  const [A12, setA12] = useState(2.0);
  const [A21, setA21] = useState(0.8);
  const [mode, setMode] = useState('gamma');
  const [showGhost, setShowGhost] = useState(false);

  const Am = (A12 + A21) / 2;

  const data = useMemo(() => {
    const pts = [];
    for (let i = 0; i <= 200; i++) {
      const x1 = i / 200;
      const x2 = 1 - x1;
      pts.push({
        x1,
        gE: x1 * x2 * (A21 * x1 + A12 * x2),
        ghost: Am * x1 * x2,
        ln1: x2 * x2 * (A12 + 2 * (A21 - A12) * x1),
        ln2: x1 * x1 * (A21 + 2 * (A12 - A21) * x2),
        g1: Math.exp(x2 * x2 * (A12 + 2 * (A21 - A12) * x1)),
        g2: Math.exp(x1 * x1 * (A21 + 2 * (A12 - A21) * x2)),
      });
    }
    return pts;
  }, [A12, A21, Am]);

  // extremo do arco (maior |gE|) e cruzamento de zero no interior
  const { xPeak, gPeak, xCross } = useMemo(() => {
    let best = data[1], cross = null;
    for (let i = 1; i < data.length - 1; i++) {
      if (Math.abs(data[i].gE) > Math.abs(best.gE)) best = data[i];
      if (data[i].gE === 0 || data[i].gE * data[i + 1].gE < 0) {
        if (i > 2 && i < data.length - 3) cross = data[i].x1;
      }
    }
    return { xPeak: best.x1, gPeak: best.gE, xCross: cross };
  }, [data]);

  const simetrico = Math.abs(A12 - A21) < 0.03;
  const g1inf = Math.exp(A12);
  const g2inf = Math.exp(A21);

  const maxG = Math.max(...data.map((d) => Math.max(d.g1, d.g2)));
  const minG = Math.min(...data.map((d) => Math.min(d.g1, d.g2)));
  const lnAll = data.flatMap((d) => [d.ln1, d.ln2]);
  const lnDom = [Math.min(0, ...lnAll) - 0.1, Math.max(0, ...lnAll) + 0.1];

  const xTicks = [0, 0.2, 0.4, 0.6, 0.8, 1];

  const seg = (id, txt) => (
    <button onClick={() => setMode(id)} style={{
      flex: 1, padding: '6px 0', fontSize: 12, fontWeight: 600, cursor: 'pointer',
      border: 'none', borderRadius: 7,
      background: mode === id ? C.ink : 'transparent',
      color: mode === id ? '#fff' : C.muted,
      fontFamily: MONO, transition: 'all .15s',
    }}>{txt}</button>
  );

  return (
    <div style={{
      minHeight: '100%', background: '#f4f6f9', padding: 16,
      fontFamily: 'ui-sans-serif, system-ui, -apple-system, sans-serif', color: C.ink,
    }}>
      <div style={{ maxWidth: 620, margin: '0 auto' }}>

        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 11, letterSpacing: 2, color: C.muted, fontFamily: MONO, textTransform: 'uppercase' }}>
            Modelo de gᴱ · demonstração interativa
          </div>
          <h1 style={{ fontSize: 24, fontWeight: 800, margin: '4px 0 8px', letterSpacing: -0.5 }}>
            Margules — 2 parâmetros
          </h1>
          <div style={{
            background: '#fff', border: '1px solid #e7ecf2', borderRadius: 10,
            padding: '10px 14px', fontSize: 14, fontFamily: MONO, color: C.ink,
            display: 'flex', flexDirection: 'column', gap: 6, overflowX: 'auto',
          }}>
            <div style={{ whiteSpace: 'nowrap' }}>
              <span style={{ color: C.gE, fontWeight: 700 }}>gᴱ/RT</span> = x₁x₂ (A₂₁x₁ + A₁₂x₂)
            </div>
            <div style={{ whiteSpace: 'nowrap' }}>
              <span style={{ color: C.g1, fontWeight: 700 }}>ln γ₁</span> = x₂² [A₁₂ + 2(A₂₁−A₁₂)x₁]
            </div>
            <div style={{ whiteSpace: 'nowrap' }}>
              <span style={{ color: C.g2, fontWeight: 700 }}>ln γ₂</span> = x₁² [A₂₁ + 2(A₁₂−A₂₁)x₂]
            </div>
          </div>
        </div>

        {/* Painel de parâmetros */}
        <div style={{
          background: '#fff', border: '1px solid #e7ecf2', borderRadius: 14,
          padding: 16, marginBottom: 14, boxShadow: '0 1px 2px rgba(15,23,42,0.03)',
        }}>
          <Slider label="A₁₂" color={C.g1} value={A12} onChange={setA12} />
          <Slider label="A₂₁" color={C.g2} value={A21} onChange={setA21} />

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 4 }}>
            <div style={{ flex: 1, background: '#f8fafc', borderRadius: 9, padding: '8px 12px', minWidth: 130 }}>
              <div style={{ fontSize: 10, color: C.muted, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                γ₁<sup>∞</sup> = e^A₁₂
              </div>
              <div style={{ fontSize: 19, fontWeight: 700, fontFamily: MONO, color: C.g1 }}>{fmt(g1inf, 2)}</div>
            </div>
            <div style={{ flex: 1, background: '#f8fafc', borderRadius: 9, padding: '8px 12px', minWidth: 130 }}>
              <div style={{ fontSize: 10, color: C.muted, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                γ₂<sup>∞</sup> = e^A₂₁
              </div>
              <div style={{ fontSize: 19, fontWeight: 700, fontFamily: MONO, color: C.g2 }}>{fmt(g2inf, 2)}</div>
            </div>
          </div>

          <div style={{
            marginTop: 8, background: simetrico ? '#ecfdf5' : '#f8fafc',
            border: simetrico ? '1px solid #a7f3d0' : '1px solid transparent',
            borderRadius: 9, padding: '8px 12px',
          }}>
            {simetrico ? (
              <div style={{ fontSize: 12, color: '#047857', fontWeight: 600 }}>
                A₁₂ = A₂₁ → o modelo se reduz a Margules-1 parâmetro. Arco simétrico, pico em 0,50.
              </div>
            ) : (
              <div style={{ fontSize: 12, color: C.muted }}>
                Extremo do arco em <b style={{ color: C.ink, fontFamily: MONO }}>x₁ = {fmt(xPeak, 2)}</b>
                {' '}· gᴱ/RT = <b style={{ color: C.ink, fontFamily: MONO }}>{fmt(gPeak, 3)}</b>
                {xCross !== null && (
                  <> · cruza zero em <b style={{ color: C.ink, fontFamily: MONO }}>x₁ = {fmt(xCross, 2)}</b></>
                )}
              </div>
            )}
          </div>
        </div>

        {/* gE */}
        <div style={{ marginBottom: 14 }}>
          <Card title="Energia de Gibbs em excesso" hint="gᴱ/RT vs x₁">
            <ResponsiveContainer width="100%" height={230}>
              <LineChart data={data} margin={{ top: 6, right: 12, bottom: 4, left: -8 }}>
                <CartesianGrid stroke={C.grid} />
                <XAxis type="number" dataKey="x1" domain={[0, 1]} ticks={xTicks}
                  tickFormatter={(v) => fmt(v, 1)} tick={{ fontSize: 11, fill: C.muted }} stroke="#cbd5e1" />
                <YAxis tick={{ fontSize: 11, fill: C.muted }} stroke="#cbd5e1" width={44} />
                <Tooltip content={<TT />} />
                <ReferenceLine y={0} stroke="#cbd5e1" />
                <ReferenceLine x={0.5} stroke="#e2e8f0" strokeDasharray="4 4" />
                <ReferenceLine x={xPeak} stroke={C.gE} strokeDasharray="2 3" strokeOpacity={0.5}
                  label={{ value: 'extremo', position: 'top', fontSize: 10, fill: C.gE }} />
                {showGhost && (
                  <Line type="monotone" dataKey="ghost" name="Margules-1" stroke={C.ghost}
                    strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
                )}
                <Line type="monotone" dataKey="gE" name="gᴱ/RT" stroke={C.gE}
                  strokeWidth={2.5} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
            <div style={{ padding: '0 4px 10px' }}>
              <button onClick={() => setShowGhost(!showGhost)} style={{
                fontSize: 11, fontFamily: MONO, cursor: 'pointer', padding: '5px 10px',
                borderRadius: 7, border: '1px solid #e2e8f0',
                background: showGhost ? '#f5f3ff' : '#fff',
                color: showGhost ? C.gE : C.muted, fontWeight: 600,
              }}>
                {showGhost ? '✓ ' : ''}comparar com Margules-1 (A = {fmt(Am, 2)})
              </button>
            </div>
          </Card>
        </div>

        {/* gammas */}
        <Card title="Coeficientes de atividade" hint={mode === 'gamma' ? 'γ vs x₁' : 'ln γ vs x₁'}>
          <div style={{ display: 'flex', gap: 4, background: '#f1f5f9', borderRadius: 9, padding: 3, marginBottom: 8 }}>
            {seg('gamma', 'γ')}{seg('ln', 'ln γ')}
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data} margin={{ top: 6, right: 12, bottom: 4, left: -8 }}>
              <CartesianGrid stroke={C.grid} />
              <XAxis type="number" dataKey="x1" domain={[0, 1]} ticks={xTicks}
                tickFormatter={(v) => fmt(v, 1)} tick={{ fontSize: 11, fill: C.muted }} stroke="#cbd5e1" />
              <YAxis domain={mode === 'gamma' ? [Math.min(0, minG * 0.9), Math.max(1.3, maxG * 1.05)] : lnDom}
                tick={{ fontSize: 11, fill: C.muted }} stroke="#cbd5e1" width={44}
                tickFormatter={(v) => fmt(v, 1)} />
              <Tooltip content={<TT />} />
              <ReferenceLine y={mode === 'gamma' ? 1 : 0} stroke={C.ideal} strokeDasharray="5 4"
                label={{ value: mode === 'gamma' ? 'ideal (γ=1)' : 'ideal (ln γ=0)', position: 'insideTopRight', fontSize: 10, fill: C.muted }} />
              <Line type="monotone" dataKey={mode === 'gamma' ? 'g1' : 'ln1'} name="γ₁"
                stroke={C.g1} strokeWidth={2.5} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey={mode === 'gamma' ? 'g2' : 'ln2'} name="γ₂"
                stroke={C.g2} strokeWidth={2.5} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', gap: 16, justifyContent: 'center', padding: '4px 0 8px', fontSize: 12, fontFamily: MONO }}>
            <span style={{ color: C.g1 }}>● γ₁ · borda esquerda = γ₁<sup>∞</sup></span>
            <span style={{ color: C.g2 }}>● γ₂ · borda direita = γ₂<sup>∞</sup></span>
          </div>
        </Card>

        {/* Guia */}
        <div style={{
          background: '#fff', border: '1px solid #e7ecf2', borderRadius: 14,
          padding: 16, marginTop: 14, fontSize: 13, lineHeight: 1.6, color: '#334155',
        }}>
          <div style={{ fontSize: 11, letterSpacing: 1.5, color: C.muted, fontFamily: MONO, textTransform: 'uppercase', marginBottom: 8 }}>
            Quatro experimentos
          </div>
          <div style={{ marginBottom: 7 }}>
            <b>1. Iguale os dois.</b> Deslize até A₁₂ = A₂₁. O painel avisa: o modelo vira Margules-1, o arco fica simétrico e o pico volta para 0,50. Essa é a <i>trava de sanidade</i> do seu app.
          </div>
          <div style={{ marginBottom: 7 }}>
            <b>2. Desequilibre.</b> Aumente só A₂₁. O arco entorta e o extremo migra para a direita — o lado do componente cujo parâmetro cresceu.
          </div>
          <div style={{ marginBottom: 7 }}>
            <b>3. Leia os parâmetros no gráfico.</b> No modo <span style={{ fontFamily: MONO }}>ln γ</span>, o valor de ln γ₁ na borda esquerda é exatamente A₁₂. E ln γ₂ na borda direita é A₂₁. Os parâmetros são medíveis.
          </div>
          <div>
            <b>4. Sinais opostos.</b> Ponha A₁₂ positivo e A₂₁ negativo. A curva <i>cruza o zero</i>: a mistura é positiva de um lado e negativa do outro. Impossível no modelo de 1 parâmetro.
          </div>
        </div>

      </div>
    </div>
  );
}
