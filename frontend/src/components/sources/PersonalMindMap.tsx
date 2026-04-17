'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { User, X } from 'lucide-react'

const nodeImageStore = new Map<string, string>()

export { nodeImageStore }

interface PersonalMindMapProps {
  data: Record<string, string>
  mainPerson: string
  sourceId: string
  sourceImageUrl?: string
}

export function PersonalMindMap({ data, mainPerson, sourceId, sourceImageUrl }: PersonalMindMapProps) {
  const fileRef = useRef<HTMLInputElement>(null)
  const centerId = `center_${sourceId}`
  const [photoUrl, setPhotoUrl] = useState<string>(nodeImageStore.get(centerId) || sourceImageUrl || '')
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [size, setSize] = useState({ w: 900, h: 620 })
  const containerRef = useRef<HTMLDivElement>(null)

  // Use source image if no custom photo uploaded
  useEffect(() => {
    if (sourceImageUrl && !nodeImageStore.get(centerId)) {
      setPhotoUrl(sourceImageUrl)
    }
  }, [sourceImageUrl, centerId])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const obs = new ResizeObserver((e) => {
      const r = e[0].contentRect
      setSize({ w: Math.max(600, Math.round(r.width)), h: Math.max(500, Math.round(r.height)) })
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      const url = ev.target?.result as string
      nodeImageStore.set(centerId, url)
      setPhotoUrl(url)
    }
    reader.readAsDataURL(file)
    e.target.value = ''
  }

  const fields = useMemo(() =>
    Object.entries(data).filter(([, v]) => v != null && String(v).trim()),
    [data]
  )

  const { w, h } = size
  const cx = w / 2
  const cy = h / 2
  const centerR = 80
  const n = Math.max(fields.length, 1)
  const orbitR = Math.min(w * 0.37, h * 0.38, 290)

  const nodes = useMemo(() => fields.map(([key, value], i) => {
    const angle = (2 * Math.PI * i) / n - Math.PI / 2
    return {
      key,
      value: String(value),
      angle,
      x: cx + orbitR * Math.cos(angle),
      y: cy + orbitR * Math.sin(angle),
    }
  }), [fields, n, cx, cy, orbitR])

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full overflow-hidden select-none"
      style={{ background: 'linear-gradient(135deg, #e8eef7 0%, #f0f4fb 100%)' }}
    >
      <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFile} />

      {/* SVG connecting lines */}
      <svg
        className="absolute inset-0 pointer-events-none"
        width={w}
        height={h}
        style={{ zIndex: 0 }}
      >
        {nodes.map((node) => (
          <g key={`line-${node.key}`}>
            <line
              x1={cx} y1={cy}
              x2={node.x} y2={node.y}
              stroke={selectedKey === node.key ? '#3b82f6' : '#b8c8d8'}
              strokeWidth={selectedKey === node.key ? 2 : 1.2}
            />
            <circle
              cx={node.x} cy={node.y} r={4}
              fill={selectedKey === node.key ? '#3b82f6' : '#94a3b8'}
            />
          </g>
        ))}
      </svg>

      {/* Center photo node */}
      <div
        className="absolute cursor-pointer group"
        style={{
          left: cx,
          top: cy,
          transform: 'translate(-50%, -50%)',
          zIndex: 10,
        }}
        onClick={() => fileRef.current?.click()}
      >
        {/* Glow */}
        <div
          className="absolute rounded-full pointer-events-none"
          style={{
            width: (centerR + 22) * 2,
            height: (centerR + 22) * 2,
            left: -(centerR + 22),
            top: -(centerR + 22),
            background: 'radial-gradient(circle, rgba(59,130,246,0.3) 0%, rgba(59,130,246,0) 70%)',
          }}
        />
        {/* Blue border ring */}
        <div
          className="absolute rounded-full"
          style={{
            width: (centerR + 6) * 2,
            height: (centerR + 6) * 2,
            left: -(centerR + 6),
            top: -(centerR + 6),
            background: '#3b82f6',
          }}
        />
        {/* White gap */}
        <div
          className="absolute rounded-full bg-white"
          style={{
            width: (centerR + 3) * 2,
            height: (centerR + 3) * 2,
            left: -(centerR + 3),
            top: -(centerR + 3),
          }}
        />
        {/* Photo circle */}
        <div
          className="relative rounded-full overflow-hidden flex items-center justify-center bg-blue-50"
          style={{ width: centerR * 2, height: centerR * 2 }}
        >
          {photoUrl ? (
            <img
              src={photoUrl}
              alt={mainPerson}
              className="w-full h-full object-cover"
              onError={() => setPhotoUrl('')}
            />
          ) : (
            <User className="text-blue-200" style={{ width: centerR * 0.65, height: centerR * 0.65 }} />
          )}
          {/* Upload hover overlay */}
          <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity rounded-full">
            <span className="text-white text-2xl">📷</span>
          </div>
        </div>

        {/* Name label */}
        <div className="absolute text-center pointer-events-none" style={{ top: centerR * 2 + 8, left: '50%', transform: 'translateX(-50%)', width: 160 }}>
          <p className="font-bold text-blue-700 text-sm leading-tight text-center">
            {mainPerson.length > 22 ? mainPerson.slice(0, 20) + '…' : mainPerson}
          </p>
          <p className="text-xs text-slate-400 mt-0.5">click to upload photo</p>
        </div>
      </div>

      {/* Field cards */}
      {nodes.map((node) => {
        const isSelected = selectedKey === node.key
        const label = node.key.replace(/_/g, ' ')
        const val = node.value
        const valShort = val.length > 30 ? val.slice(0, 28) + '…' : val

        return (
          <div
            key={node.key}
            className="absolute cursor-pointer"
            style={{
              left: node.x,
              top: node.y,
              transform: 'translate(-50%, -50%)',
              zIndex: isSelected ? 20 : 5,
            }}
            onClick={() => setSelectedKey(isSelected ? null : node.key)}
          >
            {/* Card */}
            <div
              className={`rounded-xl px-3 py-2 shadow-md border transition-all whitespace-nowrap ${
                isSelected
                  ? 'bg-blue-50 border-blue-400 shadow-blue-100 shadow-lg'
                  : 'bg-white border-slate-200 hover:border-blue-300 hover:shadow-lg'
              }`}
            >
              <span className="text-slate-500 font-semibold text-xs">{label}: </span>
              <span className="text-slate-800 text-xs font-medium">{valShort}</span>
            </div>

            {/* Full value popup for long values */}
            {isSelected && val.length > 30 && (
              <div
                className="absolute z-30 bg-white rounded-xl shadow-2xl border border-blue-200 p-3 w-60"
                style={{
                  top: node.y > cy ? 'auto' : '100%',
                  bottom: node.y > cy ? '100%' : 'auto',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  marginTop: 4,
                  marginBottom: 4,
                }}
              >
                <div className="flex justify-between items-start mb-1">
                  <p className="text-xs text-slate-400 font-semibold uppercase tracking-wide">{label}</p>
                  <button
                    onClick={(e) => { e.stopPropagation(); setSelectedKey(null) }}
                    className="text-slate-300 hover:text-slate-500 ml-2 flex-shrink-0"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
                <p className="text-sm text-slate-800 font-medium break-words">{val}</p>
              </div>
            )}
          </div>
        )
      })}

      {/* Field count badge */}
      <div className="absolute bottom-3 right-3 text-xs text-slate-400 bg-white/70 rounded-lg px-2 py-1">
        {fields.length} fields extracted
      </div>
    </div>
  )
}
