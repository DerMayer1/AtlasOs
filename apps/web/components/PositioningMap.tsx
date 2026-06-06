import type { PositioningMap as PositioningMapType } from '@atlasos/types'

interface Props {
  map: PositioningMapType
}

const W = 480
const H = 480
const PAD = 48

function toSvg(val: number, dim: number) {
  return PAD + ((val + 1) / 2) * (dim - PAD * 2)
}

export function PositioningMap({ map }: Props) {
  return (
    <div className="w-full max-w-xl mx-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" aria-label="Positioning map">
        {/* Grid lines */}
        <line x1={W / 2} y1={PAD} x2={W / 2} y2={H - PAD} stroke="#3f3f46" strokeWidth="1" />
        <line x1={PAD} y1={H / 2} x2={W - PAD} y2={H / 2} stroke="#3f3f46" strokeWidth="1" />

        {/* Axis labels */}
        <text x={PAD} y={H / 2 - 8} fontSize="10" fill="#71717a" textAnchor="middle">{map.x_axis.low}</text>
        <text x={W - PAD} y={H / 2 - 8} fontSize="10" fill="#71717a" textAnchor="middle">{map.x_axis.high}</text>
        <text x={W / 2} y={PAD - 8} fontSize="10" fill="#71717a" textAnchor="middle">{map.y_axis.high}</text>
        <text x={W / 2} y={H - PAD + 16} fontSize="10" fill="#71717a" textAnchor="middle">{map.y_axis.low}</text>

        {/* Axis titles */}
        <text x={W / 2} y={H - 8} fontSize="11" fill="#a1a1aa" textAnchor="middle" fontWeight="500">
          {map.x_axis.label}
        </text>
        <text
          x={14}
          y={H / 2}
          fontSize="11"
          fill="#a1a1aa"
          textAnchor="middle"
          fontWeight="500"
          transform={`rotate(-90, 14, ${H / 2})`}
        >
          {map.y_axis.label}
        </text>

        {/* Entities */}
        {map.entities.map((entity) => {
          const cx = toSvg(entity.x, W)
          const cy = toSvg(-entity.y, H) // invert Y
          const r = entity.is_subject ? 8 : 5
          const fill = entity.is_subject ? '#ffffff' : '#3f3f46'
          const stroke = entity.is_subject ? '#ffffff' : '#71717a'

          return (
            <g key={entity.name}>
              <circle cx={cx} cy={cy} r={r} fill={fill} stroke={stroke} strokeWidth="1.5" />
              <text
                x={cx}
                y={cy - r - 4}
                fontSize="10"
                fill={entity.is_subject ? '#ffffff' : '#a1a1aa'}
                textAnchor="middle"
                fontWeight={entity.is_subject ? '600' : '400'}
              >
                {entity.name}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
