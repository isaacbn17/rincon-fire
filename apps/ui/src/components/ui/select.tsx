import * as React from "react"

import { cn } from "@/lib/utils"

type SelectProps = React.ComponentProps<"select"> & {
  options: Array<{ label: string; value: string }>
}

export function Select({ options, className, ...props }: SelectProps) {
  return (
    <select
      className={cn(
        "h-10 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none ring-offset-background transition-colors focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
      {...props}
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  )
}
