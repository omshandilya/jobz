import { SelectHTMLAttributes, forwardRef } from "react"

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {}

const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className = "", children, ...props }, ref) => {
    return (
      <select
        className={`flex h-10 w-full rounded-md border border-gray-350 bg-white px-3 py-2 text-sm focus:outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
        ref={ref}
        {...props}
      >
        {children}
      </select>
    )
  }
)
Select.displayName = "Select"

export { Select }
