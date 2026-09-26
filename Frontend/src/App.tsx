import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type CardType = 'medication' | 'test' | 'referral' | 'next_visit' | 'general_task'

type Card = {
  id: number
  note_id: number
  type: CardType
  description: string
  description_plain: string | null
  status: 'open' | 'done'
  created_at: string
}

type NoteProcessResponse = {
  note_id: number
  cards: Card[]
}

const apiUrl = import.meta.env.VITE_API_URL ?? '/api'

const typeLabels: Record<CardType, string> = {
  medication: 'Medication',
  test: 'Test',
  referral: 'Referral',
  next_visit: 'Next visit',
  general_task: 'General task',
}

async function responseError(response: Response): Promise<string> {
  const body = await response.json().catch(() => null) as { detail?: string } | null
  return body?.detail ?? `Request failed with status ${response.status}`
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(value))
}

function CardBody({ card }: { card: Card }) {
  const [showClinical, setShowClinical] = useState(false)
  const hasPlainVersion = card.description_plain !== null && card.description_plain !== ''

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
    </>
  )
}

function App() {
  const [noteText, setNoteText] = useState('')
  const [cards, setCards] = useState<Card[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadCards() {
      try {
        const response = await fetch(`${apiUrl}/cards`)
        if (!response.ok) {
          throw new Error(await responseError(response))
        }
        const data = await response.json() as Card[]
        if (!cancelled) {
          setCards(data)
          setError(null)
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Could not load cards.')
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadCards()
    return () => {
      cancelled = true
    }
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!noteText.trim() || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setError(null)
    setSuccessMessage(null)

    try {
      const response = await fetch(`${apiUrl}/notes/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: noteText }),
      })
      if (!response.ok) {
        throw new Error(await responseError(response))
      }

      const result = await response.json() as NoteProcessResponse
      const cardsResponse = await fetch(`${apiUrl}/cards`)
      if (!cardsResponse.ok) {
        throw new Error(await responseError(cardsResponse))
      }
      setCards(await cardsResponse.json() as Card[])
      setNoteText('')
      setSuccessMessage(
        `${result.cards.length} ${result.cards.length === 1 ? 'card' : 'cards'} saved from this note.`,
      )
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Could not process the note.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="brand-mark" aria-hidden="true">CL</div>
        <div>
          <p className="eyebrow">CareLoop AI</p>
          <p className="header-caption">Notes into next steps</p>
        </div>
        <div className="header-status"><span /> Foundation flow</div>
      </header>

      <section className="intro" aria-labelledby="page-title">
        <p className="eyebrow">Care plan workspace</p>
        <h1 id="page-title">Make the next step visible.</h1>
        <p className="intro-copy">
          Paste a doctor&apos;s note and CareLoop will turn each action into a card you can follow.
        </p>
      </section>

      <section className="workspace-grid">
        <form className="note-panel" onSubmit={handleSubmit}>
          <div className="panel-heading">
            <div>
              <p className="eyebrow">01 / Add a note</p>
              <h2>What did the doctor say?</h2>
            </div>
            <span className="panel-number">A</span>
          </div>
          <label htmlFor="note-text">Doctor&apos;s note</label>
          <textarea
            id="note-text"
            value={noteText}
            onChange={(event) => setNoteText(event.target.value)}
            placeholder="Get an MRI next week. Pick up the new medication. Come back in two weeks."
            maxLength={12000}
            required
          />
          <div className="form-footer">
            <span className="character-count">{noteText.length.toLocaleString()} / 12,000</span>
            <button type="submit" disabled={isSubmitting || !noteText.trim()}>
              {isSubmitting ? 'Processing...' : 'Process note'}
              <span aria-hidden="true">-&gt;</span>
            </button>
          </div>
        </form>

        <section className="cards-panel" aria-labelledby="cards-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">02 / Your cards</p>
              <h2 id="cards-title">Every next step, in one place.</h2>
            </div>
            <span className="card-count">{cards.length}</span>
          </div>

          {error && <p className="message message-error" role="alert">{error}</p>}
          {successMessage && <p className="message message-success" role="status">{successMessage}</p>}

          {isLoading ? (
            <p className="empty-state">Loading cards...</p>
          ) : cards.length === 0 ? (
            <p className="empty-state">Your saved cards will appear here.</p>
          ) : (
            <ul className="card-list">
              {cards.map((card) => (
                <li className="task-card" key={card.id}>
                  <div className={`card-type type-${card.type}`}>
                    <span aria-hidden="true" />
                    {typeLabels[card.type]}
                  </div>
                  <CardBody card={card} />
                  <div className="card-meta">
                    <span>{card.status}</span>
                    <time dateTime={card.created_at}>{formatDate(card.created_at)}</time>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </section>
    </main>
  )
}

export default App
