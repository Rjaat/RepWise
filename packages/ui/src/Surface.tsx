import type { HTMLAttributes, ReactNode } from 'react'
import { classNames } from './classNames'

type SurfaceTone = 'light' | 'subtle' | 'dark'
export interface SurfaceProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode
  tone?: SurfaceTone
}

export function Surface({
  children,
  className,
  tone = 'light',
  ...props
}: SurfaceProps) {
  return (
    <section
      className={classNames('rw-surface', `rw-surface--${tone}`, className)}
      {...props}
    >
      {children}
    </section>
  )
}
