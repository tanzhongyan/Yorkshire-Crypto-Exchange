import type React from "react"

interface ChartProps {
  data: { name: string; value: number }[]
  index: string
  categories: string[]
  colors: string[]
  valueFormatter?: (value: number) => string
  className?: string
}

export const AreaChart: React.FC<ChartProps> = ({ data, index, categories, colors, valueFormatter, className }) => {
  return (
    <div className={className}>
      {/* Mock Area Chart */}
      <div>AreaChart Placeholder</div>
      <pre>{JSON.stringify(data)}</pre>
    </div>
  )
}

export const BarChart: React.FC<ChartProps> = ({ data, index, categories, colors, valueFormatter, className }) => {
  return (
    <div className={className}>
      {/* Mock Bar Chart */}
      <div>BarChart Placeholder</div>
      <pre>{JSON.stringify(data)}</pre>
    </div>
  )
}

