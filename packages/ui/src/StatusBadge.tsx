import type { HTMLAttributes, ReactNode } from 'react'
import { classNames } from './classNames'

export type StatusTone = 'neutral' | 'success' | 'warning' | 'error'
export interface StatusBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  children: ReactNode
  tone?: StatusTone
}

export function StatusBadge({
  children,
  className,
  tone = 'neutral',
  ...props
}: StatusBadgeProps) {
  return (
    <span
      className={classNames('rw-status', `rw-status--${tone}`, className)}
      {...props}
    >
      <span aria-hidden="true" className="rw-status__marker" />
      {children}
    </span>
  )
}
