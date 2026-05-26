package api

import (
	"encoding/json"
	"log"
	"net/http"
	"time"

	"github.com/google/uuid"
	"github.com/vektasafe/ganji-protocol/go-service/pkg/detection"
	"github.com/vektasafe/ganji-protocol/go-service/pkg/storage"
)

// Handler handles HTTP requests for the Ganji API.
type Handler struct {
	db *storage.Database
}

// NewHandler creates a new API handler.
func NewHandler(db *storage.Database) *Handler {
	return &Handler{db: db}
}

// ComputeScore handles POST /api/v1/score
func (h *Handler) ComputeScore(w http.ResponseWriter, r *http.Request) {
	var req detection.FeatureInput
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	result := detection.ComputeCIPS(req)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(result)
}

// GetLatestSignal handles GET /api/v1/signal/latest
func (h *Handler) GetLatestSignal(w http.ResponseWriter, r *http.Request) {
	// TODO: Query database for latest signal
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "not_implemented"})
}

// GetSignalArchive handles GET /api/v1/signal/archive
func (h *Handler) GetSignalArchive(w http.ResponseWriter, r *http.Request) {
	// TODO: Query database for signal archive with pagination
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "not_implemented"})
}

// BuildSignal constructs a full Signal from detection result and metadata.
func BuildSignal(result detection.DetectionResult, dataDate time.Time) detection.Signal {
	signalID := "GP-" + dataDate.Format("2006-01-02") + "-" + uuid.New().String()[:8]
	timestamp := time.Now().UTC().Format("2006-01-02T15:04:05Z")

	regulatoryNote := "This output is signal intelligence based on statistical analysis " +
		"of public data. It is not financial advice. No action is recommended " +
		"or implied. The subscriber determines how to use this information."

	return detection.Signal{
		SignalID:        signalID,
		Pair:            "KES/USD",
		Timestamp:       timestamp,
		DataDate:        dataDate.Format("2006-01-02"),
		PipelineVersion: "2.0.0", // Hybrid Go version
		Detection:       result,
		Components:      make(map[string]any),
		Context: map[string]any{
			"calendar_flags": result.CalendarFlags,
			"confidence_before_adjustment": result.ConfidenceRaw,
			"confidence_after_adjustment":  result.Confidence,
		},
		SignalContext:  "Signal intelligence from hybrid Go/PostgreSQL engine.",
		RegulatoryNote: regulatoryNote,
	}
}
