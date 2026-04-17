'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { User, MapPin, Facebook, AlertCircle, Fingerprint } from 'lucide-react'

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
  const containerRef = useRef<HTMLDivElement>(null)
  
  const centerId = `center_${sourceId}`
  const [photoUrl, setPhotoUrl] = useState<string>(nodeImageStore.get(centerId) || sourceImageUrl || '')
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [size, setSize] = useState({ w: 1200, h: 800 })

  // Transform & Pan State
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 })
  const [isDraggingCanvas, setIsDraggingCanvas] = useState(false)
  
  // Node Dragging State
  const [manualPositions, setManualPositions] = useState<Record<string, { x: number, y: number }>>({})
  const [draggedNode, setDraggedNode] = useState<{ id: string, startX: number, startY: number, initialNodeX: number, initialNodeY: number } | null>(null)
  const dragStart = useRef({ x: 0, y: 0 })

  // Initialize Source Image
  useEffect(() => {
    if (sourceImageUrl && !nodeImageStore.get(centerId)) {
      setPhotoUrl(sourceImageUrl)
    }
  }, [sourceImageUrl, centerId])

  // Handle Resize
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const obs = new ResizeObserver((e) => {
      const r = e[0].contentRect
      setSize({ w: Math.max(800, Math.round(r.width)), h: Math.max(600, Math.round(r.height)) })
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  // Handle Zoom (Wheel Event)
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault()
      const zoomSensitivity = 0.0015
      const delta = -e.deltaY * zoomSensitivity
      setTransform((prev) => ({
        ...prev,
        scale: Math.min(Math.max(0.3, prev.scale + delta), 3)
      }))
    }

    container.addEventListener('wheel', handleWheel, { passive: false })
    return () => container.removeEventListener('wheel', handleWheel)
  }, [])

  // === Mouse Event Handlers ===
  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('.interactive-node') || (e.target as HTMLElement).closest('.ui-controls')) return
    setIsDraggingCanvas(true)
    dragStart.current = { x: e.clientX - transform.x, y: e.clientY - transform.y }
  }

  const handleNodeMouseDown = (e: React.MouseEvent, id: string, currentX: number, currentY: number) => {
    e.stopPropagation()
    setDraggedNode({
      id,
      startX: e.clientX,
      startY: e.clientY,
      initialNodeX: currentX,
      initialNodeY: currentY
    })
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (draggedNode) {
      const dx = (e.clientX - draggedNode.startX) / transform.scale
      const dy = (e.clientY - draggedNode.startY) / transform.scale
      setManualPositions(prev => ({
        ...prev,
        [draggedNode.id]: {
          x: draggedNode.initialNodeX + dx,
          y: draggedNode.initialNodeY + dy
        }
      }))
    } else if (isDraggingCanvas) {
      setTransform((prev) => ({
        ...prev,
        x: e.clientX - dragStart.current.x,
        y: e.clientY - dragStart.current.y
      }))
    }
  }

  const handleMouseUp = () => {
    setIsDraggingCanvas(false)
    setDraggedNode(null)
  }

  // Handle Photo Upload
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

  const { w, h } = size
  const cx = w / 2
  const cy = h / 2
  const centerR = 85

  // Calculate Base Layout Positions with STRICT Deduplication
  const layoutNodes = useMemo(() => {
    const nodes: any[] = []
    const processedKeys = new Set<string>()

    // Always exclude Name and Alias from appearing as standalone pills
    processedKeys.add('name')
    processedKeys.add('alias')

    // 1. Top-Left Parentage Pill
    if (data['Parentage'] && data['Parentage'] !== 'N.A.') {
      processedKeys.add('parentage')
      nodes.push({
        id: 'top_parentage',
        type: 'parentage_pill',
        label: 'Parentage',
        value: data['Parentage'],
        x: cx - 220,
        y: cy - 140,
      })
    }

    // 2. Left Summary Card
    const summaryKeys = ['Parentage', 'Date of Birth', 'Age', 'Complexion']
    const summaryData = summaryKeys.reduce((acc, key) => {
      if (data[key] && data[key] !== 'N.A.') {
        acc[key] = data[key]
        processedKeys.add(key.toLowerCase())
      }
      return acc
    }, {} as Record<string, string>)

    if (Object.keys(summaryData).length > 0) {
      nodes.push({
        id: 'summary_card',
        type: 'summary',
        x: cx - 280,
        y: cy + 10,
        data: summaryData,
        title: mainPerson || data['Name']?.split('@')[0].trim() || 'Target Profile',
      })
    }

    // 3. Bottom-Left Facebook ID
    const facebookKey = Object.keys(data).find(k => k.toLowerCase().includes('facebook'))
    if (facebookKey && data[facebookKey] !== 'N.A.') {
      processedKeys.add(facebookKey.toLowerCase())
      nodes.push({
        id: 'Facebook',
        type: 'social',
        label: 'Facebook ID',
        value: data[facebookKey],
        x: cx - 320,
        y: cy + 180,
      })
    }

    // 4. Bottom Address & Alert Card
    if (data['Address'] && data['Address'] !== 'N.A.') {
      processedKeys.add('address')
      processedKeys.add('occupation') // Grouped into the criminal alert
      nodes.push({
        id: 'Address',
        type: 'address',
        value: data['Address'],
        x: cx - 20,
        y: cy + 240,
        hasAlert: data['Occupation']?.toLowerCase().includes('crime'),
      })
    }

    // 5. Bottom-Right Detail Card (Mark of Identification)
    const markKey = Object.keys(data).find(k => k.toLowerCase().includes('mark of identification'))
    if (markKey && data[markKey] !== 'N.A.') {
      processedKeys.add(markKey.toLowerCase())
      nodes.push({
        id: 'MarkOfId',
        type: 'detail_card',
        label: 'Mark of Identification',
        value: data[markKey],
        x: cx + 240,
        y: cy + 220,
      })
    }

    // 6. Right Side DYNAMIC Vertical Stack
    const rightSideEntries = Object.entries(data).filter(([k, v]) => {
      const kLow = k.toLowerCase()
      // Strict Check: If it's already rendered anywhere above, block it here
      if (processedKeys.has(kLow)) return false
      if (!v || v === 'N.A.') return false
      return true
    })

    const rightNodesConfig = rightSideEntries.map(([key, value]) => {
      const valStr = String(value);
      const isDetail = valStr.length > 30 || key.toLowerCase().includes('record') || key.toLowerCase().includes('police');
      
      let allocatedHeight = 65; 
      if (isDetail) allocatedHeight = 110 + Math.ceil(valStr.length / 40) * 20;
      
      return { key, value: valStr, type: isDetail ? 'detail_card' : 'standard', height: allocatedHeight };
    });

    const totalRightHeight = rightNodesConfig.reduce((sum, node) => sum + node.height, 0);
    let currentY = cy - (totalRightHeight / 2) + 10; 

    rightNodesConfig.forEach((nodeConfig) => {
      const distFromCenter = Math.abs(currentY - cy);
      const curveOffset = Math.pow(distFromCenter, 2) / 3000; 
      const nodeX = cx + 300 + curveOffset;

      nodes.push({
        id: `right_${nodeConfig.key}`,
        type: nodeConfig.type,
        label: nodeConfig.key,
        value: nodeConfig.value,
        x: nodeX,
        y: currentY,
      });

      currentY += nodeConfig.height;
    });

    return nodes
  }, [data, cx, cy, mainPerson])

  // Apply Manual Overrides
  const finalNodes = layoutNodes.map(node => {
    const manualPos = manualPositions[node.id]
    return {
      ...node,
      x: manualPos ? manualPos.x : node.x,
      y: manualPos ? manualPos.y : node.y
    }
  })

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full overflow-hidden select-none font-sans bg-[#f4f7fb] ${isDraggingCanvas ? 'cursor-grabbing' : 'cursor-grab'}`}
      onMouseDown={handleCanvasMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Zoom / Pan Instructions (Bottom Left) */}
      <div className="absolute bottom-4 left-4 z-50 ui-controls bg-white/80 backdrop-blur-md px-3 py-1.5 rounded-lg shadow-sm border border-slate-200 text-xs text-slate-500 font-medium pointer-events-none transition-opacity duration-200">
        Zoom: {Math.round(transform.scale * 100)}% • Scroll to zoom, Drag canvas to pan, Drag cards to move
      </div>

      <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFile} />

      {/* The Zoomable/Pannable Canvas */}
      <div 
        className="absolute inset-0 origin-center"
        style={{
          transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`,
          transition: isDraggingCanvas || draggedNode ? 'none' : 'transform 0.1s ease-out'
        }}
      >
        {/* SVG Connecting Lines */}
        <svg
          className="absolute inset-0 pointer-events-none overflow-visible"
          width={w}
          height={h}
          style={{ zIndex: 0 }}
        >
          {finalNodes.map((node) => {
            const isSelected = selectedKey === node.id
            const isDraggingThis = draggedNode?.id === node.id
            const strokeColor = isSelected || isDraggingThis ? '#3b82f6' : '#93c5fd'
            const strokeWidth = isSelected || isDraggingThis ? 2 : 1.5

            const angleToCenter = Math.atan2(node.y - cy, node.x - cx)
            const targetX = cx + (centerR + 12) * Math.cos(angleToCenter)
            const targetY = cy + (centerR + 12) * Math.sin(angleToCenter)

            // Calculate precise line end points touching card borders
            let lineEndX = node.x
            let lineEndY = node.y
            
            if (node.x > cx) {
              lineEndX = node.x - (node.type === 'detail_card' ? 130 : 110)
              if (node.type === 'address') lineEndY = node.y - 45
            } else {
              if (node.type === 'summary') lineEndX = node.x + 125
              else if (node.type === 'social') lineEndX = node.x + 130
              else if (node.type === 'parentage_pill') lineEndX = node.x + 100
              else lineEndX = node.x + 100

              if (node.type === 'address') lineEndY = node.y - 45
            }

            return (
              <g key={`line-${node.id}`}>
                <line
                  x1={targetX}
                  y1={targetY}
                  x2={lineEndX}
                  y2={lineEndY}
                  stroke={strokeColor}
                  strokeWidth={strokeWidth}
                  opacity={0.8}
                />
                <circle cx={targetX} cy={targetY} r={3.5} fill="#3b82f6" />
                <circle cx={lineEndX} cy={lineEndY} r={3.5} fill="#ffffff" stroke="#94a3b8" strokeWidth={1.5} />
              </g>
            )
          })}
        </svg>

        {/* Center Target Node */}
        <div
          className="absolute interactive-node group"
          style={{ 
            left: cx, top: cy, transform: 'translate(-50%, -50%)', 
            width: centerR * 2, height: centerR * 2, zIndex: 10 
          }}
          onClick={(e) => { e.stopPropagation(); fileRef.current?.click(); }}
        >
          <div className="absolute inset-[-14px] rounded-full bg-blue-500/15 pointer-events-none animate-pulse" />
          <div className="absolute inset-[-6px] rounded-full bg-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.4)] pointer-events-none" />
          <div className="absolute inset-[-2px] rounded-full bg-white pointer-events-none" />
          
          <div className="relative w-full h-full rounded-full overflow-hidden flex items-center justify-center bg-slate-100 shadow-inner z-10 cursor-pointer">
            {photoUrl ? (
              <img src={photoUrl} alt={mainPerson} className="w-full h-full object-cover" onError={() => setPhotoUrl('')} />
            ) : (
              <User className="text-slate-300 w-1/2 h-1/2" />
            )}
            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity text-white text-xs font-semibold backdrop-blur-[1px]">
              Upload Photo
            </div>
          </div>
        </div>

        {/* Distributed Elements */}
        {finalNodes.map((node) => {
          const isSelected = selectedKey === node.id
          const isDraggingThis = draggedNode?.id === node.id

          return (
            <div
              key={node.id}
              className={`absolute interactive-node ${isDraggingThis ? 'cursor-grabbing' : 'cursor-grab'}`}
              onMouseDown={(e) => handleNodeMouseDown(e, node.id, node.x, node.y)}
              style={{
                left: node.x,
                top: node.y,
                transform: 'translate(-50%, -50%)',
                zIndex: isSelected || isDraggingThis ? 30 : 5,
              }}
            >
              {/* 1. Top-Left Parentage Pill */}
              {node.type === 'parentage_pill' && (
                <div className="bg-white rounded-2xl shadow-sm border border-slate-200 px-4 py-2 flex flex-row items-center gap-2.5 min-w-[180px]"
                     onClick={() => setSelectedKey(isSelected ? null : node.id)}>
                  <div className="bg-blue-100 p-1.5 rounded-full shrink-0">
                    <User className="w-3.5 h-3.5 text-blue-500" />
                  </div>
                  <div className="flex flex-col pointer-events-none">
                    <span className="text-[13px] font-bold text-slate-800 leading-tight">{node.label}</span>
                    <span className="text-[12px] text-slate-600 leading-tight">{node.value}</span>
                  </div>
                </div>
              )}

              {/* 2. Left Summary Card */}
              {node.type === 'summary' && (
                <div className="bg-white rounded-[14px] shadow-sm border border-slate-200 p-4 w-[250px]"
                     onClick={() => setSelectedKey(isSelected ? null : node.id)}>
                  <h3 className="text-[16px] font-bold text-slate-800 mb-2">{node.data?.title || node.title}</h3>
                  <div className="w-full h-px bg-slate-100 mb-2.5"></div>
                  <div className="space-y-1.5">
                    {node.data && Object.entries(node.data).map(([k, v]) => (
                      <div key={k} className="flex flex-row items-baseline text-[13px] pointer-events-none">
                        <span className="text-slate-500 font-medium w-24 shrink-0">{k}:</span>
                        <span className="text-slate-800 font-semibold">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 3. Bottom Address & Criminal Tag */}
              {node.type === 'address' && (
                <div className="flex flex-col items-center" onClick={() => setSelectedKey(isSelected ? null : node.id)}>
                  <div className="bg-white rounded-t-xl shadow-sm border border-slate-200 p-3 w-[250px] relative z-10">
                    <div className="flex items-start gap-2 pointer-events-none">
                      <div className="bg-blue-100/50 p-1 rounded-full shrink-0">
                        <MapPin className="w-4 h-4 text-blue-600" />
                      </div>
                      <div>
                        <h4 className="text-[12px] text-slate-600 font-semibold mb-0.5">Address</h4>
                        <p className="text-[12px] text-slate-700 font-medium leading-snug">{node.value}</p>
                      </div>
                    </div>
                  </div>
                  {node.hasAlert && (
                    <div className="bg-[#ef4444] rounded-b-xl px-4 py-1.5 flex items-center justify-center gap-1.5 w-[250px] shadow-sm z-0">
                      <AlertCircle className="w-3.5 h-3.5 text-white" />
                      <span className="text-[12px] text-white font-bold tracking-wide">Criminal / Gangster</span>
                    </div>
                  )}
                </div>
              )}

              {/* 4. Bottom-Left Facebook ID Card */}
              {node.type === 'social' && (
                <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-3 flex flex-col w-[260px]"
                     onClick={() => setSelectedKey(isSelected ? null : node.id)}>
                  <div className="flex items-center gap-2 mb-1.5 pointer-events-none">
                    <div className="bg-[#1877F2] p-1 rounded-full">
                      <Facebook className="w-3.5 h-3.5 text-white" fill="currentColor" stroke="none" />
                    </div>
                    <span className="text-[13px] font-bold text-slate-800">{node.label}</span>
                  </div>
                  <a href={node.value.startsWith('http') ? node.value : `https://${node.value}`} target="_blank" rel="noreferrer" 
                     className="text-[12px] text-blue-600 font-medium hover:underline truncate"
                     onClick={(e) => e.stopPropagation()}>
                    {node.value}
                  </a>
                </div>
              )}

              {/* 5. Detail Card (Mark of ID, Police Station, etc.) */}
              {node.type === 'detail_card' && (
                <div className={`bg-white rounded-xl shadow-sm border p-3 flex flex-col w-[260px] transition-colors ${isSelected ? 'border-blue-400 shadow-md' : 'border-slate-200'}`}
                     onClick={() => setSelectedKey(isSelected ? null : node.id)}>
                  <div className="flex items-center gap-2 mb-2 border-b border-slate-50 pb-1.5 pointer-events-none">
                    <div className="bg-blue-50 p-1 rounded-full shrink-0">
                      <Fingerprint className="w-3.5 h-3.5 text-blue-600" />
                    </div>
                    <span className="text-[12px] font-bold text-slate-700 leading-tight">{node.label}</span>
                  </div>
                  <span className="text-[12px] text-slate-700 font-medium leading-relaxed whitespace-pre-wrap break-words pointer-events-none">
                    {node.value}
                  </span>
                </div>
              )}

              {/* 6. Standard Pills */}
              {node.type === 'standard' && (
                <div 
                  className={`rounded-full px-4 py-2 shadow-sm border transition-all flex items-center gap-1.5 whitespace-nowrap justify-center min-w-[160px] max-w-[280px] ${
                    isSelected ? 'bg-blue-50 border-blue-400 scale-105 z-20' : 'bg-white border-slate-200 hover:border-blue-300'
                  }`}
                  onClick={() => setSelectedKey(isSelected ? null : node.id)}
                >
                  <span className="text-[13px] text-slate-500 font-medium pointer-events-none">{node.label}:</span>
                  <span className="text-[13px] text-slate-800 font-medium truncate pointer-events-none">
                    {node.value}
                  </span>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}