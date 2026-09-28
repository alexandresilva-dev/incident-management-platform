import { useEffect, useState } from 'react'

interface Result<T> {
  fetcher: () => Promise<T>
  version: number
  data?: T
  error?: string
}

/**
 * Corre `fetcher` quando este muda (por isso quem chama deve estabilizá-lo com
 * useCallback) e devolve dados, erro e estado de carregamento.
 *
 * - "A carregar" é derivado: o resultado guardado pertence a outro pedido.
 * - Respostas de pedidos antigos são ignoradas (`cancelled`), por isso uma
 *   resposta lenta nunca sobrescreve uma mais recente.
 * - Os dados anteriores mantêm-se enquanto recarrega, para a UI não "piscar".
 */
export function useApi<T>(fetcher: () => Promise<T>) {
  const [result, setResult] = useState<Result<T>>()
  const [version, setVersion] = useState(0)

  useEffect(() => {
    let cancelled = false
    fetcher()
      .then((data) => {
        if (!cancelled) setResult({ fetcher, version, data })
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : String(error)
          setResult({ fetcher, version, error: message })
        }
      })
    return () => {
      cancelled = true
    }
  }, [fetcher, version])

  const isCurrent = result?.fetcher === fetcher && result.version === version
  return {
    data: result?.data,
    error: isCurrent ? result.error : undefined,
    loading: !isCurrent,
    reload: () => setVersion((v) => v + 1),
  }
}
