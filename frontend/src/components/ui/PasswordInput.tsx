import { useState, forwardRef } from 'react'
import { Eye, EyeOff } from 'lucide-react'

interface PasswordInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Classe extra aplicada ao wrapper (div externa) */
  wrapperClassName?: string
}

/**
 * PasswordInput — wrapper sobre <input type="password"> que adiciona
 * um botão olho para alternar visibilidade da senha.
 *
 * Totalmente compatível com react-hook-form via forwardRef.
 * Usa apenas CSS vars do design system — funciona em dark e light mode.
 *
 * Uso simples:
 *   <PasswordInput className="input w-full" placeholder="Sua senha" />
 *
 * Com react-hook-form:
 *   <PasswordInput {...register('password')} className="input w-full" />
 */
const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ wrapperClassName = '', className = '', style, ...props }, ref) => {
    const [visible, setVisible] = useState(false)

    return (
      <div className={`relative flex items-center ${wrapperClassName}`}>
        <input
          {...props}
          ref={ref}
          type={visible ? 'text' : 'password'}
          className={`${className} pr-10`}
          style={style}
        />
        <button
          type="button"
          tabIndex={-1}
          onClick={() => setVisible(v => !v)}
          aria-label={visible ? 'Ocultar senha' : 'Mostrar senha'}
          style={{
            position: 'absolute',
            right: 10,
            color: 'var(--color-text-faint)',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            padding: 0,
            lineHeight: 1,
          }}
        >
          {visible ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
    )
  }
)

PasswordInput.displayName = 'PasswordInput'

export default PasswordInput
