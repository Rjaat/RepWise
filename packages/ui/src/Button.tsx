import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { classNames } from './classNames'

type ButtonVariant = 'primary' | 'secondary' | 'quiet' | 'danger'
export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode
  variant?: ButtonVariant
  fullWidth?: boolean
}

export function Button({
  children,
  className,
  variant = 'primary',
  fullWidth = false,
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      className={classNames(
        'rw-button',
        `rw-button--${variant}`,
        fullWidth && 'rw-button--full',
        className,
      )}
      type={type}
      {...props}
    >
      {children}
    </button>
  )
}
