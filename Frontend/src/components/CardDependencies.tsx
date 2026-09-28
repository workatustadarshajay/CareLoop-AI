import { useState } from 'react';
import './CardDependencies.css';

interface Dependency {
  upstream_card_id: number;
  upstream_card: {
    id: number;
    description: string;
    status: string;
    type: string;
  };
  reason: string | null;
}

interface CardDependenciesProps {
  cardId: number;
  dependencies?: Dependency[];
  isAtRisk?: boolean;
  atRiskReason?: string | null;
  onDependencyCreated?: () => void;
  onDependencyDeleted?: () => void;
}

export function CardDependencies({
  cardId,
  dependencies = [],
  isAtRisk = false,
  atRiskReason = null,
  onDependencyCreated,
  onDependencyDeleted,
}: CardDependenciesProps) {
  const [showForm, setShowForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDeleteDependency = async (upstreamCardId: number) => {
    try {
      const res = await fetch(
        `/api/cards/${cardId}/dependencies/${upstreamCardId}`,
        { method: 'DELETE' }
      );

      if (!res.ok) {
        throw new Error('Failed to delete dependency');
      }

      onDependencyDeleted?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error deleting dependency');
    }
  };

  return (
    <div className="card-dependencies">
      {isAtRisk && (
        <div className="risk-badge risk-badge--at-risk">
          <span className="risk-badge__icon">⚠️</span>
          <span className="risk-badge__text">{atRiskReason}</span>
        </div>
      )}

      <div className="dependencies-section">
        <h3 className="dependencies-title">Dependencies</h3>

        {dependencies.length === 0 ? (
          <p className="dependencies-empty">No dependencies</p>
        ) : (
          <ul className="dependencies-list">
            {dependencies.map((dep) => (
              <li key={dep.upstream_card_id} className="dependency-item">
                <div className="dependency-item__main">
                  <strong className="dependency-item__description">
                    {dep.upstream_card.description}
                  </strong>
                  <span className="dependency-item__status">
                    {dep.upstream_card.status}
                  </span>
                </div>

                {dep.reason && (
                  <p className="dependency-item__reason">{dep.reason}</p>
                )}

                <button
                  className="dependency-item__delete-btn"
                  onClick={() => handleDeleteDependency(dep.upstream_card_id)}
                  title="Remove this dependency"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        )}

        {error && <p className="error-message">{error}</p>}

        <button
          className="dependencies-add-btn"
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? 'Cancel' : '+ Add Dependency'}
        </button>

        {showForm && (
          <DependencyForm
            cardId={cardId}
            isLoading={isLoading}
            setIsLoading={setIsLoading}
            setShowForm={setShowForm}
            onSuccess={onDependencyCreated}
          />
        )}
      </div>
    </div>
  );
}

interface DependencyFormProps {
  cardId: number;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  setShowForm: (show: boolean) => void;
  onSuccess?: () => void;
}

function DependencyForm({
  cardId,
  isLoading,
  setIsLoading,
  setShowForm,
  onSuccess,
}: DependencyFormProps) {
  const [upstreamCardId, setUpstreamCardId] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const res = await fetch(`/api/cards/${cardId}/dependencies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          upstream_card_id: parseInt(upstreamCardId, 10),
          reason: reason.trim() || null,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to create dependency');
      }

      setShowForm(false);
      setUpstreamCardId('');
      setReason('');
      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error creating dependency');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form className="dependency-form" onSubmit={handleSubmit}>
      <label htmlFor="upstream-card-id">Upstream Card ID</label>
      <input
        id="upstream-card-id"
        type="number"
        placeholder="Card ID this depends on"
        value={upstreamCardId}
        onChange={(e) => setUpstreamCardId(e.target.value)}
        required
        disabled={isLoading}
      />

      <label htmlFor="reason">Reason (optional)</label>
      <textarea
        id="reason"
        placeholder="Why does this card depend on the other?"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        disabled={isLoading}
        rows={3}
      />

      {error && <p className="error-message">{error}</p>}

      <div className="dependency-form__actions">
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Creating...' : 'Add Dependency'}
        </button>
      </div>
    </form>
  );
}