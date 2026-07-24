import React, { useState, useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from 'recharts';

const C = {
  g1: '#2563eb',    // componente 1 — azul
  g2: '#ea580c',    // componente 2 — laranja
  gE: '#7c3aed',    // Gibbs em excesso — violeta
  ideal: '#94a3b8', // referência ideal
  grid: '#eef2f6',
  ink: '#1e293b',
  muted: '#64748b',
};

// Pilha de fontes monoespaçadas com cobertura de grego (γ).
// ui-monospace sozinho pode cair num fallback que desenha γ parecido com "y".
const MONO = 'ui-monospace, SFMono-Regular, Menlo, "DejaVu Sans Mono", Consolas, monospace';

function fmt(v, d = 2) {
  return Number(v).toFixed(d);
}

function ChartCard({ title, hint, children }) {
  return (
    <div style={{
      background: '#fff', border: '1px solid #e7ecf2', borderRadius: 14,
      padding: '14px 12px 6px', boxShadow: '0 1px 2px rgba(15,23,42,0.03)',
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', padding: '0 4px 8px' }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: C.ink, letterSpacing: 0.2 }}>{title}</span>
        <span style={{ fontSize: 11, color: C.muted, fontFamily: MONO }}>{hint}</span>
      </div>
      {children}
    </div>
  );
}

function TT({ active, payload, label, mode }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div style={{
      background: '#0f172a', color: '#e2e8f0', borderRadius: 8, padding: '8px 10px',
      fontSize: 12, fontFamily: MONO, lineHeight: 1.5,
    }}>
      <div style={{ color: '#94a3b8', marginBottom: 2 }}>x₁ = {fmt(label, 2)}</div>
      {payload.map((p) => (
        <div key={p.name} style={{ color: p.color }}>
          {p.name} = {fmt(p.value, 3)}
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [A, setA] = useState(1.5);
  const [mode, setMode] = useState('gamma'); // 'gamma' | 'ln'

  const data = useMemo(() => {
    const pts = [];
    for (let i = 0; i <= 100; i++) {
      const x1 = i / 100;
      const x2 = 1 - x1;
      const ln1 = A * x2 * x2;
      const ln2 = A * x1 * x1;
      pts.push({ x1, gE: A * x1 * x2, g1: Math.exp(ln1), g2: Math.exp(ln2), ln1, ln2 });
    }
    return pts;
  }, [A]);

  const gInf = Math.exp(A);
  const gEmax = A / 4;

  const dev = A > 0.02
    ? { label: 'Desvio positivo', sub: 'γ > 1 · moléculas se repelem · P acima de Raoult', dot: C.g2 }
    : A < -0.02
    ? { label: 'Desvio negativo', sub: 'γ < 1 · moléculas se atraem · P abaixo de Raoult', dot: C.g1 }
    : { label: 'Mistura ideal', sub: 'γ = 1 · Lei de Raoult · sem desvio', dot: '#10b981' };

  const maxG = Math.max(...data.map((d) => Math.max(d.g1, d.g2)));
  const gammaMax = Math.max(1.25, Math.ceil(maxG * 4) / 4);
  const lnDomain = [Math.min(0, A) - 0.08, Math.max(0, A) + 0.08];

  const xTicks = [0, 0.2, 0.4, 0.6, 0.8, 1];

  const seg = (id, txt) => (
    <button
      onClick={() => setMode(id)}
      style={{
        flex: 1, padding: '6px 0', fontSize: 12, fontWeight: 600, cursor: 'pointer',
        border: 'none', borderRadius: 7,
        background: mode === id ? C.ink : 'transparent',
        color: mode === id ? '#fff' : C.muted,
        fontFamily: MONO, transition: 'all .15s',
      }}
    >{txt}</button>
  );

  return (
    <div style={{
      minHeight: '100%', background: '#f4f6f9', padding: 16,
      fontFamily: 'ui-sans-serif, system-ui, -apple-system, sans-serif', color: C.ink,
    }}>
      <div style={{ maxWidth: 620, margin: '0 auto' }}>

        {/* Header */}
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 11, letterSpacing: 2, color: C.muted, fontFamily: MONO, textTransform: 'uppercase' }}>
            Modelo de gᴱ · demonstração interativa
          </div>
          <h1 style={{ fontSize: 24, fontWeight: 800, margin: '4px 0 8px', letterSpacing: -0.5 }}>
            Margules — 1 parâmetro
          </h1>
          <div style={{
            background: '#fff', border: '1px solid #e7ecf2',
            borderRadius: 10, padding: '10px 14px', fontSize: 15,
            fontFamily: MONO, color: C.ink,
            display: 'flex', flexDirection: 'column', gap: 6,
          }}>
            {/* cada fórmula é um bloco atômico: nunca quebra no meio */}
            <div style={{ whiteSpace: 'nowrap' }}>
              <span style={{ color: C.gE, fontWeight: 700 }}>gᴱ/RT</span> = A · x₁x₂
            </div>
            <div style={{ whiteSpace: 'nowrap' }}>
              <span style={{ color: C.g1, fontWeight: 700 }}>ln γ₁</span> = A · x₂²
            </div>
            <div style={{ whiteSpace: 'nowrap' }}>
              <span style={{ color: C.g2, fontWeight: 700 }}>ln γ₂</span> = A · x₁²
            </div>
          </div>
        </div>

        {/* Parameter panel — the star */}
        <div style={{
          background: '#fff', border: '1px solid #e7ecf2', borderRadius: 14,
          padding: 16, marginBottom: 14, boxShadow: '0 1px 2px rgba(15,23,42,0.03)',
        }}>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 10 }}>
            <span style={{ fontSize: 13, fontWeight: 700 }}>Parâmetro A</span>
            <span style={{ fontSize: 32, fontWeight: 800, fontFamily: MONO, letterSpacing: -1 }}>
              {A >= 0 ? '+' : ''}{fmt(A, 2)}
            </span>
          </div>

          <input
            type="range" min={-3} max={3} step={0.05} value={A}
            onChange={(e) => setA(parseFloat(e.target.value))}
            style={{ width: '100%', accentColor: C.gE, height: 6, cursor: 'pointer' }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: C.muted, fontFamily: MONO, marginTop: 4 }}>
            <span>−3 (atração forte)</span><span>0 (ideal)</span><span>+3 (repulsão forte)</span>
          </div>

          {/* readouts */}
          <div style={{ display: 'flex', gap: 8, marginTop: 14, flexWrap: 'wrap' }}>
            <div style={{ flex: '1 1 100%', display: 'flex', alignItems: 'center', gap: 8, background: '#f8fafc', borderRadius: 9, padding: '8px 12px' }}>
              <span style={{ width: 9, height: 9, borderRadius: 9, background: dev.dot, flexShrink: 0 }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 700 }}>{dev.label}</div>
                <div style={{ fontSize: 11, color: C.muted }}>{dev.sub}</div>
              </div>
            </div>

            <div style={{ flex: 1, background: '#f8fafc', borderRadius: 9, padding: '8px 12px', minWidth: 120 }}>
              <div style={{ fontSize: 10, color: C.muted, textTransform: 'uppercase', letterSpacing: 0.5 }}>γ₁∞ · γ₂∞</div>
              <div style={{ fontSize: 18, fontWeight: 700, fontFamily: MONO }}>
                {fmt(gInf, 2)} <span style={{ color: '#cbd5e1' }}>·</span> {fmt(gInf, 2)}
              </div>
              <div style={{ fontSize: 10, color: C.gE, fontWeight: 600 }}>iguais ⇒ simetria</div>
            </div>

            <div style={{ flex: 1, background: '#f8fafc', borderRadius: 9, padding: '8px 12px', minWidth: 120 }}>
              <div style={{ fontSize: 10, color: C.muted, textTransform: 'uppercase', letterSpacing: 0.5 }}>pico gᴱ/RT</div>
              <div style={{ fontSize: 18, fontWeight: 700, fontFamily: MONO }}>{fmt(gEmax, 3)}</div>
              <div style={{ fontSize: 10, color: C.muted, fontWeight: 600 }}>em x₁ = 0,50</div>
            </div>
          </div>
        </div>

        {/* Chart 1: gE/RT */}
        <div style={{ marginBottom: 14 }}>
          <ChartCard title="Energia de Gibbs em excesso" hint="gᴱ/RT vs x₁">
            <ResponsiveContainer width="100%" height={230}>
              <LineChart data={data} margin={{ top: 6, right: 12, bottom: 4, left: -8 }}>
                <CartesianGrid stroke={C.grid} />
                <XAxis type="number" dataKey="x1" domain={[0, 1]} ticks={xTicks}
                  tickFormatter={(v) => fmt(v, 1)} tick={{ fontSize: 11, fill: C.muted }}
                  stroke="#cbd5e1" />
                <YAxis tick={{ fontSize: 11, fill: C.muted }} stroke="#cbd5e1" width={44} />
                <Tooltip content={<TT />} />
                <ReferenceLine y={0} stroke="#cbd5e1" />
                <ReferenceLine x={0.5} stroke="#e2e8f0" strokeDasharray="4 4"
                  label={{ value: 'eixo de simetria', position: 'top', fontSize: 10, fill: '#a3aec0' }} />
                <Line type="monotone" dataKey="gE" name="gᴱ/RT" stroke={C.gE}
                  strokeWidth={2.5} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>

        {/* Chart 2: gammas */}
        <ChartCard title="Coeficientes de atividade" hint={mode === 'gamma' ? 'γ vs x₁' : 'ln γ vs x₁'}>
          <div style={{ display: 'flex', gap: 4, background: '#f1f5f9', borderRadius: 9, padding: 3, marginBottom: 8 }}>
            {seg('gamma', 'γ')}{seg('ln', 'ln γ')}
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data} margin={{ top: 6, right: 12, bottom: 4, left: -8 }}>
              <CartesianGrid stroke={C.grid} />
              <XAxis type="number" dataKey="x1" domain={[0, 1]} ticks={xTicks}
                tickFormatter={(v) => fmt(v, 1)} tick={{ fontSize: 11, fill: C.muted }}
                stroke="#cbd5e1" />
              <YAxis domain={mode === 'gamma' ? [0, gammaMax] : lnDomain}
                tick={{ fontSize: 11, fill: C.muted }} stroke="#cbd5e1" width={44}
                tickFormatter={(v) => fmt(v, mode === 'gamma' ? 1 : 1)} />
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
            <span style={{ color: C.g1 }}>● γ₁ (comp. 1)</span>
            <span style={{ color: C.g2 }}>● γ₂ (comp. 2)</span>
          </div>
        </ChartCard>

        {/* Reading guide */}
        <div style={{
          background: '#fff', border: '1px solid #e7ecf2', borderRadius: 14,
          padding: 16, marginTop: 14, fontSize: 13, lineHeight: 1.6, color: '#334155',
        }}>
          <div style={{ fontSize: 11, letterSpacing: 1.5, color: C.muted, fontFamily: MONO, textTransform: 'uppercase', marginBottom: 8 }}>
            O que observar enquanto você arrasta A
          </div>
          <div style={{ marginBottom: 6 }}>
            <b>1. Botão de volume.</b> Afaste A de zero e as curvas se afastam da linha ideal. Volte a zero: tudo vira reta (Raoult).
          </div>
          <div style={{ marginBottom: 6 }}>
            <b>2. Simetria.</b> O arco de gᴱ mantém o pico sempre em x₁ = 0,50, colado no eixo tracejado — não importa o valor de A. Essa é a assinatura (e a limitação) do modelo de 1 parâmetro.
          </div>
          <div style={{ marginBottom: 6 }}>
            <b>3. Pureza ⇒ γ → 1.</b> Nas bordas, cada γ toca a linha ideal: γ₁ → 1 quando x₁ → 1, e γ₂ → 1 quando x₁ → 0. Trava de sanidade universal do seu app.
          </div>
          <div>
            <b>4. Diluição infinita.</b> γ₁∞ e γ₂∞ (o valor de cada γ na borda oposta) são <i>sempre iguais</i> aqui. No modelo de 2 parâmetros, eles deixam de ser — é o próximo passo.
          </div>
        </div>

      </div>
    </div>
  );
}
