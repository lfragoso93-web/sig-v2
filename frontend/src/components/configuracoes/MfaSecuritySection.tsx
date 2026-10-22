import { useState, useEffect } from 'react'
import {
  ShieldCheck,
  ShieldAlert,
  Copy,
  Check,
  Loader2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import api from '@/services/api'
import { getApiValidationErrorMessage } from '@/utils/apiError'

interface MfaStatus {
  mfa_enabled: boolean
  auth_provider: string
}

interface MfaSetupData {
  secret: string
  uri: string
  backup_codes: string[]
}

export default function MfaSecuritySection() {
  const [status, setStatus] = useState<MfaStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)

  // Estados de Setup
  const [setupData, setSetupData] = useState<MfaSetupData | null>(null)
  const [confirmCode, setConfirmCode] = useState('')
  const [isEnabling, setIsEnabling] = useState(false)
  const [copiedKey, setCopiedKey] = useState(false)
  const [copiedCodes, setCopiedCodes] = useState(false)

  // Estados de Desativação
  const [disableMode, setDisableMode] = useState(false)
  const [disableCode, setDisableCode] = useState('')
  const [isDisabling, setIsDisabling] = useState(false)

  // Feedback
  const [feedback, setFeedback] = useState<{ msg: string; isError: boolean } | null>(null)

  const loadStatus = async () => {
    try {
      const { data } = await api.get<MfaStatus>('/auth/mfa/status')
      setStatus(data)
    } catch {
      // Ignora falha de consulta se offline
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadStatus()
  }, [])

  const startSetup = async () => {
    setFeedback(null)
    setLoading(true)
    try {
      const { data } = await api.post<MfaSetupData>('/auth/mfa/setup')
      setSetupData(data)
      setDisableMode(false)
    } catch (err: unknown) {
      setFeedback({
        msg: getApiValidationErrorMessage(err, 'Erro ao iniciar configuração de MFA.'),
        isError: true,
      })
    } finally {
      setLoading(false)
    }
  }

  const handleEnableMfa = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!setupData || !confirmCode.trim()) return
    setFeedback(null)
    setIsEnabling(true)
    try {
      await api.post('/auth/mfa/enable', {
        secret: setupData.secret,
        code: confirmCode.trim(),
        backup_codes: setupData.backup_codes,
      })
      setFeedback({
        msg: 'Autenticação em duas etapas ativada com sucesso!',
        isError: false,
      })
      setSetupData(null)
      setConfirmCode('')
      await loadStatus()
    } catch (err: unknown) {
      setFeedback({
        msg: getApiValidationErrorMessage(err, 'Código inválido. Verifique e tente novamente.'),
        isError: true,
      })
    } finally {
      setIsEnabling(false)
    }
  }

  const handleDisableMfa = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!disableCode.trim()) return
    setFeedback(null)
    setIsDisabling(true)
    try {
      await api.post('/auth/mfa/disable', { code: disableCode.trim() })
      setFeedback({
        msg: 'Autenticação em duas etapas desativada.',
        isError: false,
      })
      setDisableMode(false)
      setDisableCode('')
      await loadStatus()
    } catch (err: unknown) {
      setFeedback({
        msg: getApiValidationErrorMessage(err, 'Código incorreto. Não foi possível desativar.'),
        isError: true,
      })
    } finally {
      setIsDisabling(false)
    }
  }

  const copyToClipboard = (text: string, type: 'key' | 'codes') => {
    void navigator.clipboard.writeText(text)
    if (type === 'key') {
      setCopiedKey(true)
      setTimeout(() => setCopiedKey(false), 2000)
    } else {
      setCopiedCodes(true)
      setTimeout(() => setCopiedCodes(false), 2000)
    }
  }

  return (
    <section className="card settings-card">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center justify-between w-full"
      >
        <div className="flex items-center gap-2">
          <ShieldCheck size={15} style={{ color: 'var(--color-primary)' }} />
          <h2
            className="text-xs font-semibold uppercase tracking-wide"
            style={{ color: 'var(--color-text-muted)' }}
          >
            Autenticação em Duas Etapas (MFA / 2FA)
          </h2>
          {status && (
            <span
              className="text-[10px] px-2 py-0.5 rounded-full font-medium ml-2"
              style={{
                background: status.mfa_enabled
                  ? 'oklch(from var(--color-success) l c h / 0.15)'
                  : 'oklch(from var(--color-text-muted) l c h / 0.12)',
                color: status.mfa_enabled
                  ? 'var(--color-success)'
                  : 'var(--color-text-muted)',
              }}
            >
              {status.mfa_enabled ? 'Ativado' : 'Opcional (Desativado)'}
            </span>
          )}
        </div>
        {open ? (
          <ChevronUp size={14} style={{ color: 'var(--color-text-faint)' }} />
        ) : (
          <ChevronDown size={14} style={{ color: 'var(--color-text-faint)' }} />
        )}
      </button>

      {open && (
        <div className="mt-3 flex flex-col gap-3">
          <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
            Adicione uma camada extra de segurança à sua conta exigindo um código de verificação
            do seu celular ou computador (compatível com Google Authenticator, Authy, Bitwarden e 1Password).
          </p>

          {feedback && (
            <div
              className="text-xs px-3 py-2 rounded-lg"
              style={{
                color: feedback.isError ? 'var(--color-error)' : 'var(--color-success)',
                background: feedback.isError
                  ? 'oklch(from var(--color-error) l c h / 0.1)'
                  : 'oklch(from var(--color-success) l c h / 0.1)',
              }}
            >
              {feedback.msg}
            </div>
          )}

          {/* Estado: MFA NÃO ATIVADO e sem setup aberto */}
          {!status?.mfa_enabled && !setupData && (
            <div>
              <button
                type="button"
                onClick={startSetup}
                disabled={loading}
                className="btn btn-primary text-xs"
                style={{ minHeight: 36 }}
              >
                {loading ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  'Configurar e Ativar 2FA'
                )}
              </button>
            </div>
          )}

          {/* Painel de Configuração Inicial do MFA */}
          {!status?.mfa_enabled && setupData && (
            <div
              className="p-4 rounded-xl flex flex-col gap-4"
              style={{
                background: 'var(--color-surface-offset)',
                border: '1px solid var(--color-border)',
              }}
            >
              <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                1. Chave Secreta de Configuração
              </h3>
              <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                No seu app autenticador, selecione <strong>Adicionar conta</strong> e insira a chave abaixo:
              </p>

              <div className="flex items-center gap-2">
                <code
                  className="px-3 py-2 rounded-lg font-mono text-xs font-semibold tracking-wider flex-1"
                  style={{
                    background: 'var(--color-surface)',
                    border: '1px solid var(--color-divider)',
                    color: 'var(--color-primary)',
                  }}
                >
                  {setupData.secret}
                </code>
                <button
                  type="button"
                  onClick={() => copyToClipboard(setupData.secret, 'key')}
                  className="btn btn-ghost text-xs flex items-center gap-1.5"
                  style={{ minHeight: 34 }}
                >
                  {copiedKey ? <Check size={13} /> : <Copy size={13} />}
                  <span>{copiedKey ? 'Copiada' : 'Copiar'}</span>
                </button>
              </div>

              <h3 className="text-sm font-semibold mt-2" style={{ color: 'var(--color-text)' }}>
                2. Códigos de Recuperação Descartáveis
              </h3>
              <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                Guarde estes códigos em local seguro. Caso perca acesso ao seu app autenticador,
                cada código poderá ser usado uma única vez para entrar na sua conta.
              </p>

              <div className="grid grid-cols-2 gap-2">
                {setupData.backup_codes.map((c, i) => (
                  <div
                    key={i}
                    className="font-mono text-xs p-1.5 rounded text-center tracking-widest"
                    style={{
                      background: 'var(--color-surface)',
                      border: '1px solid var(--color-divider)',
                      color: 'var(--color-text)',
                    }}
                  >
                    {c}
                  </div>
                ))}
              </div>

              <div>
                <button
                  type="button"
                  onClick={() =>
                    copyToClipboard(setupData.backup_codes.join('\n'), 'codes')
                  }
                  className="btn btn-ghost text-xs flex items-center gap-1.5"
                  style={{ minHeight: 30 }}
                >
                  {copiedCodes ? <Check size={13} /> : <Copy size={13} />}
                  <span>{copiedCodes ? 'Códigos Copiados!' : 'Copiar todos os códigos'}</span>
                </button>
              </div>

              <h3 className="text-sm font-semibold mt-2" style={{ color: 'var(--color-text)' }}>
                3. Confirme com o código gerado
              </h3>

              <form onSubmit={handleEnableMfa} className="flex flex-col gap-3">
                <input
                  type="text"
                  maxLength={6}
                  placeholder="000000"
                  className="input font-mono text-center tracking-widest text-base w-48"
                  value={confirmCode}
                  onChange={(e) => setConfirmCode(e.target.value)}
                  autoFocus
                />

                <div className="flex items-center gap-2">
                  <button
                    type="submit"
                    disabled={isEnabling || confirmCode.trim().length !== 6}
                    className="btn btn-primary text-xs"
                    style={{ minHeight: 36 }}
                  >
                    {isEnabling ? (
                      <Loader2 size={13} className="animate-spin" />
                    ) : (
                      'Confirmar e Ativar 2FA'
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => setSetupData(null)}
                    className="btn btn-ghost text-xs"
                  >
                    Cancelar
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Estado: MFA JÁ ATIVADO */}
          {status?.mfa_enabled && (
            <div className="flex flex-col gap-3">
              <div
                className="p-3 rounded-lg flex items-center gap-3 text-xs"
                style={{
                  background: 'oklch(from var(--color-success) l c h / 0.08)',
                  border: '1px solid oklch(from var(--color-success) l c h / 0.2)',
                  color: 'var(--color-success)',
                }}
              >
                <ShieldCheck size={18} />
                <span>
                  Sua conta está protegida com autenticação de dois fatores ativa.
                </span>
              </div>

              {!disableMode ? (
                <div>
                  <button
                    type="button"
                    onClick={() => setDisableMode(true)}
                    className="btn btn-ghost text-xs"
                    style={{ color: 'var(--color-notification)' }}
                  >
                    Desativar 2FA
                  </button>
                </div>
              ) : (
                <form
                  onSubmit={handleDisableMfa}
                  className="p-3 rounded-xl flex flex-col gap-2"
                  style={{
                    background: 'var(--color-surface-offset)',
                    border: '1px solid var(--color-border)',
                  }}
                >
                  <div className="flex items-center gap-1.5 text-xs font-semibold" style={{ color: 'var(--color-text)' }}>
                    <ShieldAlert size={14} style={{ color: 'var(--color-notification)' }} />
                    <span>Confirmação para Desativar 2FA</span>
                  </div>
                  <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                    Insira um código do seu app autenticador ou um código de recuperação para confirmar:
                  </p>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      placeholder="Código de 6 dígitos"
                      className="input font-mono text-xs w-48"
                      value={disableCode}
                      onChange={(e) => setDisableCode(e.target.value)}
                      autoFocus
                    />
                    <button
                      type="submit"
                      disabled={isDisabling || !disableCode.trim()}
                      className="btn text-xs font-semibold"
                      style={{
                        background: 'var(--color-notification)',
                        color: 'white',
                        minHeight: 34,
                      }}
                    >
                      {isDisabling ? (
                        <Loader2 size={13} className="animate-spin" />
                      ) : (
                        'Desativar'
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setDisableMode(false)
                        setDisableCode('')
                      }}
                      className="btn btn-ghost text-xs"
                    >
                      Cancelar
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
