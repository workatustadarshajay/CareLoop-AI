import { useCallback, useEffect, useRef, useState } from 'react'
import type { ComponentProps, FormEvent } from 'react'
import { CardDependencies } from './components/CardDependencies'
import { Landing } from './Landing'
import { LOGOUT_EVENT, apiUrl, getAuth, responseError, setAuth } from './api'
import type { Auth, Role } from './api'
import './App.css'

type CardType = 'medication' | 'test' | 'referral' | 'next_visit' | 'general_task'
type CardStatus = 'open' | 'done' | 'at_risk' | 'blocked' | 'verified_closed'

type Card = {
  id: number
  note_id: number
  type: CardType
  description: string
  description_plain: string | null
  status: CardStatus
  risk_reason: string | null
  due_at: string | null
  patient_id: number | null
  created_at: string
}

type NoteProcessResponse = {
  note_id: number
  cards: Card[]
  closed_card_ids: number[]
}

type Patient = { id: number; name: string; username: string | null }
type Reminder = { id: number; card_id: number; message: string; created_at: string }
type Recommendation = {
  id: number
  note_id: number
  patient_id: number | null
  reason: string
  diagnosis: string | null
  item_label: string | null
  card_type: CardType | null
  card_description: string | null
}

type PatientFilter = number | 'all'
type StatusFilter = 'all' | 'open' | 'at_risk' | 'overdue' | 'closed'

/** Account record as the administrator screen sees it. */
type AccountRow = {
  id: number
  username: string
  role: Role
  patient_id: number | null
  patient_name: string | null
}

const roleLabels: Record<Role, string> = {
  patient: 'Patient',
  care_coordinator: 'Care coordinator',
  doctor: 'Doctor',
  admin: 'Administrator',
}

const roleOptions: Role[] = ['patient', 'care_coordinator', 'doctor', 'admin']

const typeLabels: Record<CardType, string> = {
  medication: 'Medication',
  test: 'Test',
  referral: 'Referral',
  next_visit: 'Next visit',
  general_task: 'General task',
}

const statusOptions: CardStatus[] = ['open', 'done', 'blocked', 'verified_closed']
const CLOSED: CardStatus[] = ['done', 'verified_closed']
const DAY = 86_400_000

const isOpen = (card: Card) => !CLOSED.includes(card.status)
const isOverdue = (card: Card) => isOpen(card) && card.due_at !== null && new Date(card.due_at).getTime() < Date.now()
const isDueSoon = (card: Card) => isOpen(card) && card.due_at !== null && !isOverdue(card) && new Date(card.due_at).getTime() < Date.now() + 7 * DAY

const statusFilters: { key: StatusFilter; label: string; match: (card: Card) => boolean }[] = [
  { key: 'all', label: 'All', match: () => true },
  { key: 'open', label: 'Open', match: isOpen },
  { key: 'at_risk', label: 'At risk', match: (card) => card.status === 'at_risk' },
  { key: 'overdue', label: 'Overdue', match: isOverdue },
  { key: 'closed', label: 'Closed', match: (card) => CLOSED.includes(card.status) },
]

const testAccounts = [
  { username: 'admin', label: 'Administrator' },
  { username: 'dr_smith', label: 'Doctor' },
  { username: 'coordinator', label: 'Care coordinator' },
  { username: 'alice', label: 'Patient: Alice' },
  { username: 'bob', label: 'Patient: Bob' },
]

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(value))
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, init)
  if (!response.ok) {
    throw new Error(await responseError(response))
  }
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>)
}

function Login({ onLogin, onBack }: { onLogin: (auth: Auth) => void; onBack: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSubmitting(true)
    setError(null)
    try {
      const auth = await fetchJson<Auth>('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      setAuth(auth)
      onLogin(auth)
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : 'Could not log in.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form className="note-panel login-panel" onSubmit={handleSubmit}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Sign in</p>
          <h2>Who are you?</h2>
        </div>
        <button type="button" className="card-toggle" onClick={onBack}>← Back</button>
      </div>
      <label htmlFor="username">Username</label>
      <input id="username" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
      <label htmlFor="password">Password</label>
      <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
      {error && <p className="message message-error" role="alert">{error}</p>}
      <p className="eyebrow">Test accounts (password: password)</p>
      <div className="chip-row">
        {testAccounts.map((account) => (
          <button
            key={account.username}
            type="button"
            className="chip"
            onClick={() => { setUsername(account.username); setPassword('password') }}
          >
            {account.label} · {account.username}
          </button>
        ))}
      </div>
      <div className="form-footer">
        <span />
        <button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Signing in...' : 'Sign in'}</button>
      </div>
    </form>
  )
}

function CardBody({ card, canEdit, onChanged }: { card: Card; canEdit: boolean; onChanged: () => void }) {
  const [showClinical, setShowClinical] = useState(false)
  const [dependencies, setDependencies] = useState<ComponentProps<typeof CardDependencies>['dependencies']>([])

  const hasPlainVersion = card.description_plain !== null && card.description_plain !== ''

  useEffect(() => {
    // Fetch dependencies for this card
    fetch(`${apiUrl}/cards/${card.id}/dependencies`)
      .then(res => res.json())
      .then(data => setDependencies(data.dependencies || []))
      .catch(err => console.error('Error fetching dependencies:', err))
  }, [card.id, card.status])

  return (
    <>
      <p className="card-description">
        {hasPlainVersion ? card.description_plain : card.description}
      </p>
      {hasPlainVersion && (
        <div className="card-clinical-section">
          <button
            type="button"
            className="card-toggle"
            aria-expanded={showClinical}
            onClick={() => setShowClinical((current) => !current)}
          >
            {showClinical ? 'Hide clinical wording' : 'Show clinical wording'}
          </button>
          {showClinical && <p className="card-clinical">{card.description}</p>}
        </div>
      )}

      <CardDependencies
        cardId={card.id}
        dependencies={dependencies}
        isAtRisk={card.status === 'at_risk'}
        atRiskReason={card.risk_reason}
        canEdit={canEdit}
        onDependencyCreated={onChanged}
        onDependencyDeleted={onChanged}
      />
    </>
  )
}

/** Doctor-only: change status or due date. Closing a card re-checks anything that depends on it. */
function CardControls({ card, onChanged }: { card: Card; onChanged: () => void }) {
  const [error, setError] = useState<string | null>(null)

  async function patch(body: Partial<Pick<Card, 'status' | 'due_at'>>) {
    setError(null)
    try {
      await fetchJson(`/cards/${card.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      onChanged()
    } catch (patchError) {
      setError(patchError instanceof Error ? patchError.message : 'Could not update card.')
    }
  }

  return (
    <div className="card-controls">
      <label htmlFor={`status-${card.id}`}>Status</label>
      <select
        id={`status-${card.id}`}
        value={card.status}
        onChange={(e) => void patch({ status: e.target.value as CardStatus })}
      >
        {card.status === 'at_risk' && <option value="at_risk">at_risk (auto)</option>}
        {statusOptions.map((status) => <option key={status} value={status}>{status}</option>)}
      </select>
      <label htmlFor={`due-${card.id}`}>Due</label>
      <input
        id={`due-${card.id}`}
        type="date"
        value={card.due_at ? card.due_at.slice(0, 10) : ''}
        onChange={(e) => void patch({ due_at: e.target.value ? `${e.target.value}T09:00:00Z` : null })}
      />
      {error && <p className="error-message">{error}</p>}
    </div>
  )
}

/** Doctor-only: pick which patient's cards to show. Native <dialog>, no modal library. */
function PatientPicker({
  patients, cards, value, onChange, onClose,
}: {
  patients: Patient[]
  cards: Card[]
  value: PatientFilter
  onChange: (next: PatientFilter) => void
  onClose: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const [query, setQuery] = useState('')
  useEffect(() => { ref.current?.showModal() }, [])

  const needle = query.trim().toLowerCase()
  const matches = patients.filter((p) => !needle || p.name.toLowerCase().includes(needle) || String(p.id) === needle)

  const counts = (filter: PatientFilter) => {
    const own = cards.filter((card) => filter === 'all' || card.patient_id === filter)
    return `${own.filter((c) => !CLOSED.includes(c.status)).length} open · ${own.filter((c) => c.status === 'at_risk').length} at risk`
  }
  const choose = (next: PatientFilter) => { onChange(next); onClose() }

  return (
    <dialog ref={ref} className="picker" onClose={onClose} onClick={(e) => { if (e.target === ref.current) onClose() }}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Show cards for</p>
          <h2>Choose a patient</h2>
        </div>
        <button type="button" className="card-toggle" onClick={onClose}>Close</button>
      </div>
      <input
        type="search"
        className="picker-search"
        placeholder="Search patients by name or id…"
        aria-label="Search patients"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        autoFocus
      />
      <ul className="picker-list">
        {!needle && (
          <li>
            <button type="button" className={value === 'all' ? 'picker-option selected' : 'picker-option'} onClick={() => choose('all')}>
              <strong>All patients</strong><span>{counts('all')}</span>
            </button>
          </li>
        )}
        {matches.length === 0 && <li className="dependencies-empty">No patient matches “{query}”.</li>}
        {matches.map((p) => (
          <li key={p.id}>
            <button type="button" className={value === p.id ? 'picker-option selected' : 'picker-option'} onClick={() => choose(p.id)}>
              <strong>{p.name}</strong><span>{counts(p.id)}</span>
            </button>
          </li>
        ))}
      </ul>
    </dialog>
  )
}

/**
 * Administrator-only: add or update a login. A patient account always carries the
 * patient record, so its role is fixed; staff accounts can be re-roled.
 */
function AccountDialog({
  account, onSaved, onClose,
}: {
  account?: AccountRow
  onSaved: (account: AccountRow, mode: 'create' | 'edit') => void
  onClose: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const isEdit = account !== undefined
  const isPatientAccount = account?.patient_id != null
  const [role, setRole] = useState<Role>(account?.role ?? 'patient')
  const [name, setName] = useState(account?.patient_name ?? '')
  const [username, setUsername] = useState(account?.username ?? '')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  useEffect(() => { ref.current?.showModal() }, [])

  const showsNameField = role === 'patient'

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    if (!isEdit && !password) {
      setError('Set a temporary password for this new login.')
      return
    }
    setIsSubmitting(true)
    try {
      const body: Record<string, unknown> = { username }
      if (password) {
        body.password = password
      }
      if (showsNameField) {
        body.name = name
      }
      if (!isEdit) {
        body.role = role
      } else if (!isPatientAccount && role !== account.role) {
        body.role = role
      }
      const saved = await fetchJson<AccountRow>(isEdit ? `/accounts/${account.id}` : '/accounts', {
        method: isEdit ? 'PATCH' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      onSaved(saved, isEdit ? 'edit' : 'create')
      onClose()
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save this account.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <dialog ref={ref} className="picker" onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Administrator</p>
            <h2>{isEdit ? `Update ${account.username}` : 'New account'}</h2>
          </div>
          <button type="button" className="card-toggle" onClick={onClose}>Close</button>
        </div>
        <label htmlFor="ac-role">Role</label>
        <select
          id="ac-role"
          value={role}
          onChange={(e) => setRole(e.target.value as Role)}
          disabled={isPatientAccount}
        >
          {roleOptions.map((option) => <option key={option} value={option}>{roleLabels[option]}</option>)}
        </select>
        {showsNameField && (
          <>
            <label htmlFor="ac-name">Patient name</label>
            <input id="ac-name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={200} />
          </>
        )}
        <label htmlFor="ac-username">Login username</label>
        <input id="ac-username" value={username} onChange={(e) => setUsername(e.target.value)} required pattern="[A-Za-z0-9_.-]+" minLength={2} autoComplete="off" />
        <label htmlFor="ac-password">{isEdit ? 'New password (leave blank to keep)' : 'Temporary password'}</label>
        <input id="ac-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={6} required={!isEdit} autoComplete="new-password" />
        {isEdit && isPatientAccount && (
          <p className="eyebrow">A patient login keeps the patient role.</p>
        )}
        {error && <p className="message message-error" role="alert">{error}</p>}
        <div className="form-footer">
          <span className="character-count">
            {showsNameField ? 'The patient signs in with these details.' : 'Staff logins are not linked to a patient.'}
          </span>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : isEdit ? 'Save changes' : 'Create account'}
          </button>
        </div>
      </form>
    </dialog>
  )
}

/** Administrator-only: confirm removal. A patient account takes the plan with it. */
function DeleteAccount({
  account, onDeleted, onClose,
}: {
  account: AccountRow
  onDeleted: (message: string) => void
  onClose: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  useEffect(() => { ref.current?.showModal() }, [])

  async function confirm() {
    setIsDeleting(true)
    setError(null)
    try {
      const result = await fetchJson<{ message?: string }>(`/accounts/${account.id}`, { method: 'DELETE' })
      onDeleted(result?.message ?? `Deleted “${account.username}”.`)
      onClose()
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Could not delete this account.')
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <dialog ref={ref} className="picker" onClose={onClose}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Delete</p>
          <h2>{account.patient_name ?? account.username}</h2>
        </div>
        <button type="button" className="card-toggle" onClick={onClose}>Cancel</button>
      </div>
      <p>
        {account.patient_id !== null
          ? `${account.patient_name} is removed together with the login “${account.username}”, every note and every card in their plan.`
          : `The ${roleLabels[account.role].toLowerCase()} login “${account.username}” is removed.`}
      </p>
      {error && <p className="message message-error" role="alert">{error}</p>}
      <div className="form-footer">
        <span className="character-count">This cannot be undone.</span>
        <button type="button" onClick={() => void confirm()} disabled={isDeleting}>
          {isDeleting ? 'Deleting...' : 'Delete'}
        </button>
      </div>
    </dialog>
  )
}

/** Doctor-only: care-gap recommendations, hidden by default. Approve creates the card; dismiss hides the flag. */
function Recommendations({ items, onChanged }: { items: Recommendation[]; onChanged: () => void }) {
  const [show, setShow] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function act(id: number, action: 'approve' | 'dismiss') {
    setError(null)
    try {
      await fetchJson(`/review-flags/${id}/${action}`, { method: 'POST' })
      onChanged()
    } catch (actError) {
      setError(actError instanceof Error ? actError.message : 'Could not update recommendation.')
    }
  }

  return (
    <section className="note-panel recommendations-panel" aria-labelledby="recs-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Recommendations</p>
          <h2 id="recs-title">Usually part of the care plan</h2>
        </div>
        <span className="panel-number">{items.length}</span>
      </div>
      <button type="button" className="card-toggle" aria-expanded={show} onClick={() => setShow((s) => !s)}>
        {show ? 'Hide recommendations' : `Show recommendations (${items.length})`}
      </button>
      {show && (
        items.length === 0 ? (
          <p className="empty-state">No open recommendations.</p>
        ) : (
          <ul className="recommendation-list">
            {items.map((rec) => (
              <li key={rec.id} className="recommendation">
                <p className="eyebrow">{rec.diagnosis} · {rec.card_type ? typeLabels[rec.card_type] : 'item'}</p>
                <strong>{rec.card_description ?? rec.item_label}</strong>
                <p>{rec.reason}</p>
                <div className="chip-row">
                  <button type="button" className="chip" onClick={() => void act(rec.id, 'approve')}>Add as card</button>
                  <button type="button" className="chip chip-muted" onClick={() => void act(rec.id, 'dismiss')}>Dismiss</button>
                </div>
              </li>
            ))}
          </ul>
        )
      )}
      {error && <p className="error-message">{error}</p>}
    </section>
  )
}

/** At-a-glance numbers for whatever set of cards is currently in view. */
function Summary({ cards }: { cards: Card[] }) {
  const stats = [
    { label: 'Open', value: cards.filter(isOpen).length },
    { label: 'At risk', value: cards.filter((c) => c.status === 'at_risk').length, tone: 'risk' },
    { label: 'Overdue', value: cards.filter(isOverdue).length, tone: 'overdue' },
    { label: 'Due in 7 days', value: cards.filter(isDueSoon).length },
    { label: 'Closed', value: cards.filter((c) => CLOSED.includes(c.status)).length, tone: 'muted' },
  ]
  return (
    <dl className="summary">
      {stats.map((stat) => (
        <div key={stat.label} className={`stat ${stat.tone ?? ''} ${stat.value === 0 ? 'zero' : ''}`}>
          <dt>{stat.label}</dt>
          <dd>{stat.value}</dd>
        </div>
      ))}
    </dl>
  )
}

/** Administrators manage every login: patients, doctors, care coordinators and other administrators. */
type AccountDialogState =
  | { mode: 'create' }
  | { mode: 'edit'; account: AccountRow }
  | { mode: 'delete'; account: AccountRow }

function AdminView() {
  const [accounts, setAccounts] = useState<AccountRow[]>([])
  const [query, setQuery] = useState('')
  const [dialog, setDialog] = useState<AccountDialogState | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchJson<AccountRow[]>('/accounts').then(setAccounts).catch((e) => setError(e instanceof Error ? e.message : 'Could not load accounts.'))
  }, [])

  const needle = query.trim().toLowerCase()
  const shown = accounts.filter((a) => !needle
    || a.username.toLowerCase().includes(needle)
    || (a.patient_name ?? '').toLowerCase().includes(needle)
    || roleLabels[a.role].toLowerCase().includes(needle)
    || String(a.id) === needle)
  const staffCount = accounts.filter((a) => a.patient_id === null).length

  function upsert(row: AccountRow, mode: 'create' | 'edit') {
    setAccounts((list) => {
      const next = mode === 'create' ? [...list, row] : list.map((a) => (a.id === row.id ? row : a))
      return next.sort((a, b) => a.username.localeCompare(b.username))
    })
    setMessage(mode === 'create'
      ? `Created the ${roleLabels[row.role].toLowerCase()} login “${row.username}”${row.patient_name ? ` for ${row.patient_name}` : ''}.`
      : `Updated “${row.username}”.`)
  }

  return (
    <>
      <section className="intro" aria-labelledby="page-title">
        <p className="eyebrow">Administration</p>
        <h1 id="page-title">People and their logins.</h1>
        <p className="intro-copy">
          Add, update or remove patients, doctors and care coordinators. Patients open a read-only plan;
          care coordinators and doctors work on the plans.
        </p>
      </section>

      <section className="cards-panel admin-panel" aria-labelledby="accounts-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Accounts</p>
            <h2 id="accounts-title">Everyone with a login.</h2>
          </div>
          <span className="card-count">{accounts.length}</span>
        </div>

        <div className="toolbar">
          <input
            type="search"
            className="picker-search"
            placeholder="Search by name, username, role or id…"
            aria-label="Search accounts"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="button" className="chip" onClick={() => setDialog({ mode: 'create' })}>+ New account</button>
        </div>

        {error && <p className="message message-error" role="alert">{error}</p>}
        {message && <p className="message message-success" role="status">{message}</p>}

        {shown.length === 0 ? (
          <p className="empty-state">{accounts.length === 0 ? 'No accounts yet.' : `No account matches “${query}”.`}</p>
        ) : (
          <table className="patient-table">
            <thead>
              <tr><th>Id</th><th>Patient</th><th>Login username</th><th>Role</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {shown.map((row) => (
                <tr key={row.id}>
                  <td className="mono"># {row.id}</td>
                  <td>{row.patient_name ?? <span className="dependencies-empty">not a patient</span>}</td>
                  <td className="mono">{row.username}</td>
                  <td><span className="role-tag">{roleLabels[row.role]}</span></td>
                  <td className="row-actions">
                    <button type="button" className="card-toggle" onClick={() => setDialog({ mode: 'edit', account: row })}>Update</button>
                    <button type="button" className="card-toggle" onClick={() => setDialog({ mode: 'delete', account: row })}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="character-count">{accounts.length} logins · {staffCount} staff</p>
      </section>

      {dialog?.mode === 'create' && <AccountDialog onClose={() => setDialog(null)} onSaved={upsert} />}
      {dialog?.mode === 'edit' && (
        <AccountDialog account={dialog.account} onClose={() => setDialog(null)} onSaved={upsert} />
      )}
      {dialog?.mode === 'delete' && (
        <DeleteAccount
          account={dialog.account}
          onClose={() => setDialog(null)}
          onDeleted={(text) => {
            setAccounts((list) => list.filter((a) => a.id !== dialog.account.id))
            setMessage(text)
          }}
        />
      )}
    </>
  )
}

function Workspace({ auth }: { auth: Auth }) {
  const isDoctor = auth.role === 'doctor'
  // Care coordinators work on any patient's plan but make no clinical calls.
  const isCoordinator = auth.role === 'care_coordinator'
  const isCareTeam = isDoctor || isCoordinator
  const canReview = isDoctor
  const [noteText, setNoteText] = useState('')
  const [cards, setCards] = useState<Card[]>([])
  const [patients, setPatients] = useState<Patient[]>([])
  const [patientFilter, setPatientFilter] = useState<PatientFilter | null>(null)
  const [notePatientId, setNotePatientId] = useState<number | ''>('')
  const [showPicker, setShowPicker] = useState(false)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [reminders, setReminders] = useState<Reminder[]>([])
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // One card list for both roles; the API already filters by who is logged in.
  const refresh = useCallback(async () => {
    try {
      const [nextCards, nextReminders, nextRecs] = await Promise.all([
        fetchJson<Card[]>('/cards'),
        isDoctor ? Promise.resolve([]) : fetchJson<Reminder[]>('/reminders'),
        canReview ? fetchJson<Recommendation[]>('/review-flags') : Promise.resolve([]),
      ])
      setCards(nextCards)
      setReminders(nextReminders)
      setRecommendations(nextRecs)
      setError(null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load cards.')
    } finally {
      setIsLoading(false)
    }
  }, [isDoctor, canReview])

  useEffect(() => {
    void Promise.resolve().then(refresh)
    if (isCareTeam) {
      // Doctors start on their first patient; the picker widens the view to everyone.
      fetchJson<Patient[]>('/patients')
        .then((list) => {
          setPatients(list)
          setPatientFilter(list[0]?.id ?? 'all')
          setNotePatientId(list[0]?.id ?? '')
        })
        .catch(() => setPatients([]))
    }
  }, [refresh, isCareTeam])

  const patientName = (id: number | null) => patients.find((p) => p.id === id)?.name ?? (id ? `Patient ${id}` : 'Unassigned')
  const inPatientFilter = (id: number | null) => !isCareTeam || patientFilter === 'all' || patientFilter === null || id === patientFilter
  const patientCards = cards.filter((card) => inPatientFilter(card.patient_id))
  const visibleCards = patientCards.filter(statusFilters.find((f) => f.key === statusFilter)!.match)
  const visibleRecs = recommendations.filter((rec) => inPatientFilter(rec.patient_id))
  const reminderPatient = (reminder: Reminder) => cards.find((card) => card.id === reminder.card_id)?.patient_id ?? null
  const visibleReminders = reminders.filter((reminder) => inPatientFilter(reminderPatient(reminder)))

  function choosePatient(next: PatientFilter) {
    setPatientFilter(next)
    if (next !== 'all') {
      setNotePatientId(next)
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!noteText.trim() || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setError(null)
    setSuccessMessage(null)

    try {
      const result = await fetchJson<NoteProcessResponse>('/notes/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: noteText, patient_id: isCareTeam ? notePatientId || null : undefined }),
      })
      await refresh()
      setNoteText('')
      const saved = `${result.cards.length} ${result.cards.length === 1 ? 'card' : 'cards'} saved`
      const closed = result.closed_card_ids.length
        ? `, ${result.closed_card_ids.length} closed as verified done`
        : ''
      setSuccessMessage(`${saved}${closed} from this note.`)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Could not process the note.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <section className="intro" aria-labelledby="page-title">
        <p className="eyebrow">{isCareTeam ? 'All patients' : 'Your care plan'}</p>
        <h1 id="page-title">Make the next step visible.</h1>
        <p className="intro-copy">
          {isDoctor
            ? "Paste a doctor's note for a patient and CareLoop will turn each action into a card they can follow."
            : isCoordinator
              ? 'Choose a patient, then add an update note. CareLoop closes the matching card and re-checks anything that was waiting on it.'
              : "Your doctor's next steps in plain language, with reminders for what is coming up. Your care coordinator keeps this plan up to date."}
        </p>
      </section>

      <section className="workspace-grid">
        <div className="side-column">
          {isCareTeam ? (
            <form className="note-panel" onSubmit={handleSubmit}>
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">{isDoctor ? '01 / Add a note' : '01 / Update a plan'}</p>
                  <h2>{isDoctor ? 'What did the doctor say?' : 'What has changed for this patient?'}</h2>
                </div>
                <span className="panel-number">A</span>
              </div>
              <label htmlFor="patient">Patient</label>
              <select
                id="patient"
                value={notePatientId}
                onChange={(e) => setNotePatientId(e.target.value ? Number(e.target.value) : '')}
                required
              >
                <option value="">Choose a patient</option>
                {patients.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <label htmlFor="note-text">{isDoctor ? "Doctor's note" : 'Update note'}</label>
              <textarea
                id="note-text"
                value={noteText}
                onChange={(event) => setNoteText(event.target.value)}
                placeholder={isDoctor
                  ? 'Get an MRI next week. Pick up the new medication. Come back in two weeks.'
                  : 'Fasting lipid panel completed this morning at the lab.'}
                maxLength={12000}
                required
              />
              <div className="form-footer">
                <span className="character-count">{noteText.length.toLocaleString()} / 12,000</span>
                <button type="submit" disabled={isSubmitting || !noteText.trim() || !notePatientId}>
                  {isSubmitting ? 'Processing...' : isDoctor ? 'Process note' : 'Add update'}
                  <span aria-hidden="true">-&gt;</span>
                </button>
              </div>
            </form>
          ) : (
            <section className="note-panel read-only-panel" aria-labelledby="read-only-title">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Your plan</p>
                  <h2 id="read-only-title">Kept up to date for you</h2>
                </div>
                <span className="panel-number">A</span>
              </div>
              <p className="empty-state">
                Your care coordinator updates this plan after each visit or call, so the cards here are the
                current version. Tell your care team if something looks out of date.
              </p>
            </section>
          )}

          {canReview && <Recommendations items={visibleRecs} onChanged={() => void refresh()} />}

          {!isDoctor && (
            <section className="note-panel reminders-panel" aria-labelledby="reminders-title">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">{isCoordinator ? 'Reminders' : 'Your reminders'}</p>
                  <h2 id="reminders-title">Coming up</h2>
                </div>
                <span className="panel-number">{visibleReminders.length}</span>
              </div>
              {visibleReminders.length === 0 ? (
                <p className="empty-state">Nothing due soon.</p>
              ) : (
                <ul className="reminder-list">
                  {visibleReminders.map((reminder) => (
                    <li key={reminder.id} className={reminder.message.startsWith('Overdue') ? 'reminder overdue' : 'reminder'}>
                      {reminder.message}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}
        </div>

        <section className="cards-panel" aria-labelledby="cards-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">02 / {isCareTeam ? (patientFilter === 'all' ? 'All patients' : patientName(patientFilter)) : 'Your cards'}</p>
              <h2 id="cards-title">Every next step, in one place.</h2>
            </div>
            <span className="card-count">{visibleCards.length}</span>
          </div>

          <Summary cards={patientCards} />

          <div className="toolbar">
            <div className="chip-row" role="group" aria-label="Filter by status">
              {statusFilters.map((f) => (
                <button
                  key={f.key}
                  type="button"
                  className={statusFilter === f.key ? 'chip selected' : 'chip'}
                  aria-pressed={statusFilter === f.key}
                  onClick={() => setStatusFilter(f.key)}
                >
                  {f.label}
                </button>
              ))}
            </div>
            {isCareTeam && (
              <button type="button" className="chip" onClick={() => setShowPicker(true)}>
                Choose patient…
              </button>
            )}
          </div>

          {error && <p className="message message-error" role="alert">{error}</p>}
          {successMessage && <p className="message message-success" role="status">{successMessage}</p>}

          {isLoading ? (
            <p className="empty-state">Loading cards...</p>
          ) : visibleCards.length === 0 ? (
            <p className="empty-state">{cards.length === 0 ? (isCareTeam ? 'No cards yet.' : 'Your cards will appear here.') : 'No cards match this filter.'}</p>
          ) : (
            <ul className="card-list">
              {visibleCards.map((card) => (
                <li className={`task-card status-${card.status} ${isOverdue(card) ? 'overdue' : ''}`} key={card.id}>
                  <div className={`card-type type-${card.type}`}>
                    <span aria-hidden="true" />
                    {typeLabels[card.type]}
                    <span className="card-id"># {card.id}</span>
                    {isCareTeam && <span className="card-patient">{patientName(card.patient_id)}</span>}
                  </div>
                  <CardBody card={card} canEdit={isCareTeam} onChanged={() => void refresh()} />
                  {isCareTeam && <CardControls card={card} onChanged={() => void refresh()} />}
                  <div className="card-meta">
                    <span>{card.status.replace('_', ' ')}</span>
                    {card.status === 'at_risk' && (
                      <span className="risk-badge">⚠️ At Risk</span>
                    )}
                    {isOverdue(card) && <span className="overdue-badge">Overdue</span>}
                    {card.due_at && <span className="due">Due {formatDate(card.due_at)}</span>}
                    <time dateTime={card.created_at}>{formatDate(card.created_at)}</time>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </section>

      {showPicker && patientFilter !== null && (
        <PatientPicker
          patients={patients}
          cards={cards}
          value={patientFilter}
          onChange={choosePatient}
          onClose={() => setShowPicker(false)}
        />
      )}
    </>
  )
}

function App() {
  const [auth, setAuthState] = useState<Auth | null>(getAuth)
  const [showLogin, setShowLogin] = useState(false)

  useEffect(() => {
    const onLogout = () => setAuthState(null)
    window.addEventListener(LOGOUT_EVENT, onLogout)
    return () => window.removeEventListener(LOGOUT_EVENT, onLogout)
  }, [])

  function logout() {
    setAuth(null)
    setAuthState(null)
    setShowLogin(false)
  }

  if (!auth && !showLogin) {
    return <Landing onSignIn={() => setShowLogin(true)} />
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="brand-mark" aria-hidden="true">CL</div>
        <div>
          <p className="eyebrow">CareLoop AI</p>
          <p className="header-caption">Notes into next steps</p>
        </div>
        <div className="header-status">
          <span />
          {auth ? (
            <>
              {auth.username} · {roleLabels[auth.role]}
              <button type="button" className="card-toggle" onClick={logout}>Log out</button>
            </>
          ) : 'Signed out'}
        </div>
      </header>

      {auth ? (auth.role === 'admin' ? <AdminView key={auth.token} /> : <Workspace key={auth.token} auth={auth} />) : <Login onLogin={setAuthState} onBack={() => setShowLogin(false)} />}
    </main>
  )
}

export default App
