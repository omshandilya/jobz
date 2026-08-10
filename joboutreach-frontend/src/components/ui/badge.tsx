import { HTMLAttributes } from "react"

export interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'outline' | 'destructive'
}

export function Badge({ className = "", variant = 'default', ...props }: BadgeProps) {
  const baseStyles = "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none"
  
  const variants = {
    default: "border-transparent bg-indigo-600 text-white hover:bg-indigo-700",
    secondary: "border-transparent bg-gray-100 text-gray-800",
    destructive: "border-transparent bg-red-500 text-white hover:bg-red-600",
    outline: "text-gray-900 border border-gray-200 bg-white"
  }

  return (
    <div
      className={`${baseStyles} ${variants[variant]} ${className}`}
      {...props}
    />
  )
}
