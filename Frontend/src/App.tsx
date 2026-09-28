import { useCallback, useEffect, useRef, useState } from 'react'
import type { ComponentProps, FormEvent } from 'react'
import { CardDependencies } from './components/CardDependencies'
import { Landing } from './Landing'
import { LOGOUT_EVENT, apiUrl, getAuth, responseError, setAuth } from './api'
import type { Auth } from './api'
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

function CardBody({ card, onChanged }: { card: Card; onChanged: () => void }) {
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

/** Administrator-only: create a patient and their login in one step. */
function NewPatient({ onCreated, onClose }: { onCreated: (patient: Patient) => void; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const [name, setName] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  useEffect(() => { ref.current?.showModal() }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSubmitting(true)
    setError(null)
    try {
      const patient = await fetchJson<Patient>('/patients', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, username, password }),
      })
      onCreated(patient)
      onClose()
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Could not create patient.')
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
            <h2>New patient</h2>
          </div>
          <button type="button" className="card-toggle" onClick={onClose}>Close</button>
        </div>
        <label htmlFor="np-name">Full name</label>
        <input id="np-name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={200} />
        <label htmlFor="np-username">Login username</label>
        <input id="np-username" value={username} onChange={(e) => setUsername(e.target.value)} required pattern="[A-Za-z0-9_.-]+" minLength={2} autoComplete="off" />
        <label htmlFor="np-password">Temporary password</label>
        <input id="np-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} autoComplete="new-password" />
        {error && <p className="message message-error" role="alert">{error}</p>}
        <div className="form-footer">
          <span className="character-count">The patient logs in with these details.</span>
          <button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Creating...' : 'Create patient'}</button>
        </div>
      </form>
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

/** Administrators manage patients only: no notes, cards or recommendations. */
function AdminView() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [query, setQuery] = useState('')
  const [showNewPatient, setShowNewPatient] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchJson<Patient[]>('/patients').then(setPatients).catch((e) => setError(e instanceof Error ? e.message : 'Could not load patients.'))
  }, [])

  const needle = query.trim().toLowerCase()
  const shown = patients.filter((p) => !needle || p.name.toLowerCase().includes(needle) || (p.username ?? '').toLowerCase().includes(needle) || String(p.id) === needle)

  return (
    <>
      <section className="intro" aria-labelledby="page-title">
        <p className="eyebrow">Administration</p>
        <h1 id="page-title">Patients and logins.</h1>
        <p className="intro-copy">Create patients and their logins here. Doctors and patients do the clinical work.</p>
      </section>

      <section className="cards-panel admin-panel" aria-labelledby="patients-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Patients</p>
            <h2 id="patients-title">Everyone with a login.</h2>
          </div>
          <span className="card-count">{patients.length}</span>
        </div>

        <div className="toolbar">
          <input
            type="search"
            className="picker-search"
            placeholder="Search by name, username or id…"
            aria-label="Search patients"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="button" className="chip" onClick={() => setShowNewPatient(true)}>+ New patient</button>
        </div>

        {error && <p className="message message-error" role="alert">{error}</p>}
        {message && <p className="message message-success" role="status">{message}</p>}

        {shown.length === 0 ? (
          <p className="empty-state">{patients.length === 0 ? 'No patients yet.' : `No patient matches “${query}”.`}</p>
        ) : (
          <table className="patient-table">
            <thead>
              <tr><th>Id</th><th>Name</th><th>Login username</th></tr>
            </thead>
            <tbody>
              {shown.map((p) => (
                <tr key={p.id}>
                  <td className="mono"># {p.id}</td>
                  <td>{p.name}</td>
                  <td className="mono">{p.username ?? <span className="dependencies-empty">no login</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {showNewPatient && (
        <NewPatient
          onClose={() => setShowNewPatient(false)}
          onCreated={(patient) => {
            setPatients((list) => [...list, patient].sort((a, b) => a.name.localeCompare(b.name)))
            setMessage(`Patient ${patient.name} created. They can log in as “${patient.username}” now.`)
          }}
        />
      )}
    </>
  )
}

function Workspace({ auth }: { auth: Auth }) {
  const isDoctor = auth.role === 'doctor'
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
        isDoctor ? fetchJson<Recommendation[]>('/review-flags') : Promise.resolve([]),
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
  }, [isDoctor])

  useEffect(() => {
    void Promise.resolve().then(refresh)
    if (isDoctor) {
      // Doctors start on their first patient; the picker widens the view to everyone.
      fetchJson<Patient[]>('/patients')
        .then((list) => {
          setPatients(list)
          setPatientFilter(list[0]?.id ?? 'all')
          setNotePatientId(list[0]?.id ?? '')
        })
        .catch(() => setPatients([]))
    }
  }, [refresh, isDoctor])

  const patientName = (id: number | null) => patients.find((p) => p.id === id)?.name ?? (id ? `Patient ${id}` : 'Unassigned')
  const inPatientFilter = (id: number | null) => !isDoctor || patientFilter === 'all' || patientFilter === null || id === patientFilter
  const patientCards = cards.filter((card) => inPatientFilter(card.patient_id))
  const visibleCards = patientCards.filter(statusFilters.find((f) => f.key === statusFilter)!.match)
  const visibleRecs = recommendations.filter((rec) => inPatientFilter(rec.patient_id))

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
        body: JSON.stringify({ text: noteText, patient_id: isDoctor ? notePatientId || null : undefined }),
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
        <p className="eyebrow">{isDoctor ? 'All patients' : 'Your care plan'}</p>
        <h1 id="page-title">Make the next step visible.</h1>
        <p className="intro-copy">
          {isDoctor
            ? "Paste a doctor's note for a patient and CareLoop will turn each action into a card they can follow."
            : "Your doctor's next steps, and reminders for what's coming up. Add a note when you've completed something."}
        </p>
      </section>

      <section className="workspace-grid">
        <div className="side-column">
          <form className="note-panel" onSubmit={handleSubmit}>
            <div className="panel-heading">
              <div>
                <p className="eyebrow">01 / Add a note</p>
                <h2>{isDoctor ? 'What did the doctor say?' : 'What have you done?'}</h2>
              </div>
              <span className="panel-number">A</span>
            </div>
            {isDoctor && (
              <>
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
              </>
            )}
            <label htmlFor="note-text">{isDoctor ? "Doctor's note" : 'Follow-up note'}</label>
            <textarea
              id="note-text"
              value={noteText}
              onChange={(event) => setNoteText(event.target.value)}
              placeholder={isDoctor
                ? 'Get an MRI next week. Pick up the new medication. Come back in two weeks.'
                : 'MRI completed this morning.'}
              maxLength={12000}
              required
            />
            <div className="form-footer">
              <span className="character-count">{noteText.length.toLocaleString()} / 12,000</span>
              <button type="submit" disabled={isSubmitting || !noteText.trim() || (isDoctor && !notePatientId)}>
                {isSubmitting ? 'Processing...' : 'Process note'}
                <span aria-hidden="true">-&gt;</span>
              </button>
            </div>
          </form>

          {isDoctor && <Recommendations items={visibleRecs} onChanged={() => void refresh()} />}

          {!isDoctor && (
            <section className="note-panel reminders-panel" aria-labelledby="reminders-title">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Your reminders</p>
                  <h2 id="reminders-title">Coming up</h2>
                </div>
                <span className="panel-number">{reminders.length}</span>
              </div>
              {reminders.length === 0 ? (
                <p className="empty-state">Nothing due soon.</p>
              ) : (
                <ul className="reminder-list">
                  {reminders.map((reminder) => (
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
              <p className="eyebrow">02 / {isDoctor ? (patientFilter === 'all' ? 'All patients' : patientName(patientFilter)) : 'Your cards'}</p>
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
            {isDoctor && (
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
            <p className="empty-state">{cards.length === 0 ? (isDoctor ? 'No cards yet.' : 'Your cards will appear here.') : 'No cards match this filter.'}</p>
          ) : (
            <ul className="card-list">
              {visibleCards.map((card) => (
                <li className={`task-card status-${card.status} ${isOverdue(card) ? 'overdue' : ''}`} key={card.id}>
                  <div className={`card-type type-${card.type}`}>
                    <span aria-hidden="true" />
                    {typeLabels[card.type]}
                    <span className="card-id"># {card.id}</span>
                    {isDoctor && <span className="card-patient">{patientName(card.patient_id)}</span>}
                  </div>
                  <CardBody card={card} onChanged={() => void refresh()} />
                  {isDoctor && <CardControls card={card} onChanged={() => void refresh()} />}
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
              {auth.username} · {auth.role === 'admin' ? 'Administrator' : auth.role === 'doctor' ? 'Doctor' : 'Patient'}
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
