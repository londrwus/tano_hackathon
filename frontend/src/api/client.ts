/* ============================================================
   CLIENT — tries the real endpoint, falls back to the mock on ANY
   failure (network, non-200, bad JSON, timeout, contract error flag).
   Which one it used goes to the CONSOLE. Never to the screen.
   ============================================================ */

import {
  mockAsk,
  mockCard,
  mockCase,
  mockOnboard,
  mockOverride,
  mockQueue,
  mockQueueAction,
  mockRedecide,
  mockStandard,
} from './mock'
import type {
  AskBody,
  AskResponse,
  CardPayload,
  CasePayload,
  OnboardPayload,
  QueueActionResponse,
  QueuePayload,
  RedecideBody,
  StandardPayload,
} from './types'

const TIMEOUT_MS = 2500

export type Source = 'live' | 'mock'

export interface Result<T> {
  data: T
  source: Source
}

function log(source: Source, path: string, why?: unknown) {
  if (source === 'live') {
    console.info(`[api] LIVE  ${path}`)
  } else {
    console.warn(`[api] MOCK  ${path}`, why ?? '(backend unreachable)')
  }
}

async function request<T>(
  path: string,
  init: RequestInit | undefined,
  fallback: () => T,
): Promise<Result<T>> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS)
  try {
    const res = await fetch(path, {
      ...init,
      signal: ctrl.signal,
      headers: init?.body
        ? { 'Content-Type': 'application/json', ...(init?.headers ?? {}) }
        : init?.headers,
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const json = (await res.json()) as T & { error?: string; fallback?: boolean }
    /* Contract §7: a failure still returns 200 with an `error` sentence.
       Treat that as a failure for sourcing purposes but still render it —
       the backend's frozen cache beats ours when it exists. */
    if (json && typeof json === 'object' && 'error' in json && json.error) {
      log('live', path)
      console.warn(`[api] backend reported a handled failure on ${path}: ${json.error}`)
      return { data: json, source: 'live' }
    }
    log('live', path)
    return { data: json, source: 'live' }
  } catch (err) {
    log('mock', path, err)
    return { data: fallback(), source: 'mock' }
  } finally {
    clearTimeout(timer)
  }
}

/* ---- 1 ---- */
export const getCase = () => request<CasePayload>('/api/case', undefined, () => mockCase)

/* ---- 2 ---- */
export const getStandard = () =>
  request<StandardPayload>('/api/standard', undefined, () => mockStandard)

export const postStandardOverride = (overrides: Record<string, number>) =>
  request<QueuePayload>(
    '/api/standard/override',
    { method: 'POST', body: JSON.stringify({ overrides }) },
    () => mockOverride(overrides),
  )

/* ---- 3 ---- */
export const getQueue = () => request<QueuePayload>('/api/queue', undefined, () => mockQueue)

export const postQueueAction = (
  id: string,
  action: 'send' | 'edit' | 'hold',
  text?: string,
) =>
  request<QueueActionResponse>(
    `/api/queue/${id}/action`,
    { method: 'POST', body: JSON.stringify({ action, text: text ?? null }) },
    () => mockQueueAction(action),
  )

/* ---- 4 ---- */
export const postAsk = (body: AskBody) =>
  request<AskResponse>(
    '/api/ask',
    { method: 'POST', body: JSON.stringify(body) },
    () => mockAsk(body.skin, body.budget),
  )

/* ---- 5 ---- */
export const getCard = (cardId: string) =>
  request<CardPayload>(`/api/card/${cardId}`, undefined, () => mockCard(cardId))

export const postRedecide = (cardId: string, body: RedecideBody) =>
  request<CardPayload>(
    `/api/card/${cardId}/redecide`,
    { method: 'POST', body: JSON.stringify(body) },
    () => mockRedecide(cardId, body.skin, body.budget),
  )

/* ---- 6 ---- */
export const getOnboard = (handle: string) =>
  request<OnboardPayload>(
    `/api/onboard?handle=${encodeURIComponent(handle)}`,
    undefined,
    () => ({ ...mockOnboard, handle }),
  )
