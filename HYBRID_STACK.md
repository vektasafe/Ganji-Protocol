# Ganji Protocol - Hybrid Stack (Go + PostgreSQL)

This branch contains the production-grade hybrid architecture migration.

## Architecture

### Python Layer (Unchanged)
- **Data ingestion**: `engine/data_layer.py`
- **Feature engineering**: `engine/features.py`
- **Validation**: `tests/test_engine.py`
- **Research**: `research/`, `README.md`

Stay here for:
- Signal research and model development
- Threshold tuning and backtesting
- Historical validation
- NLP model training

### Go Service Layer (New)
- **Core scoring engine**: `go-service/pkg/detection/scorer.go`
- **HTTP API**: `go-service/pkg/api/handler.go`
- **Storage**: `go-service/pkg/storage/db.go`
- **Database**: PostgreSQL with migrations in `db/migrations/`

### Migration Strategy: Gradual Rollout

**Phase 1 (Weeks 1-2): Build & Validate**
- Build Go service with CIPS scoring logic ported from Python
- Deploy PostgreSQL with schema migration
- Run Python feature layer, feed outputs to Go service
- Compare outputs: Go service must match Python on all test signals

**Phase 2 (Weeks 3-4): Parallel Operation**
- Deploy Go service alongside Python pipeline
- Python fetches data + computes features
- Go service receives features, computes CIPS, stores in PostgreSQL
- Monitor both systems producing identical signals

**Phase 3 (Weeks 5-8): Migration & Stabilization**
- Gradually shift incoming signals to Go service
- Keep Python as fallback/validation
- Full cutover to Go + PostgreSQL
- Archive Python feature cache

## Getting Started

### Prerequisites
- Go 1.22+
- PostgreSQL 16+
- Docker & Docker Compose (optional, for local dev)

### Local Development with Docker

```bash
cd /path/to/ganji-protocol
docker-compose up
```

This spins up:
- PostgreSQL on `localhost:5432`
- Go service on `localhost:8080`

### Manual Setup

```bash
# 1. Create PostgreSQL database
createdb ganji_protocol

# 2. Run migrations
psql ganji_protocol < db/migrations/001_initial_schema.sql

# 3. Build and run Go service
cd go-service
go build -o ganji-service ./cmd/ganji-service
./ganji-service
```

### Environment Variables

```bash
DATABASE_URL=postgres://user:pass@localhost:5432/ganji_protocol
PORT=8080
```

## API Endpoints

### Health Check
```
GET /health
```

### Compute CIPS Score
```
POST /api/v1/score
Content-Type: application/json

{
  "f1_zscore": 2.5,
  "f1_zscore_fired": true,
  "f2_cpii_fired": true,
  "f2_cpii_value": 1.8,
  "f3_gvci_fired": true,
  "f3_gvci_value": 0.25,
  "f4_rss_fired": false,
  "f5_nlp_tone": "NEUTRAL",
  "f6_bpps_fired": false,
  "f6_bpps_premium": 0.001,
  "f6_cbk_suppression": false,
  "f7_calendar_flags": []
}
```

Response:
```json
{
  "cips_score": 6,
  "confidence": "HIGH",
  "confidence_raw": "HIGH",
  "direction": "KES_SUPPORT",
  "sequence_pattern": true,
  "cpii_contributed": true,
  "calendar_flags": [],
  "components": {
    "z_score_low": 1,
    "z_score_high": 1,
    "cpii": 3,
    "gvci": 2
  }
}
```

### Get Latest Signal
```
GET /api/v1/signal/latest
```

### Get Signal Archive
```
GET /api/v1/signal/archive?limit=100&offset=0
```

## Database Schema

### `rates` table
- Historical daily rates for EAC pairs
- Indexed by (currency, date DESC)

### `signals` table
- Complete signal archive with CIPS breakdown
- Indexed by (signal_date DESC), (confidence), (signal_id)

### `p2p_snapshots` table
- Binance P2P data for BPPS feature

### `pipeline_runs` table
- Audit log of data collection runs

## Testing

Python tests remain in `tests/test_engine.py`. Run:
```bash
cd /path/to/ganji-protocol
python -m pytest tests/
```

Go tests (to be added):
```bash
cd go-service
go test ./pkg/detection -v
```

## Validation Checklist

- [ ] Go service builds and starts without errors
- [ ] PostgreSQL schema loads correctly
- [ ] Python + Go CIPS scores match on test dataset
- [ ] Health check returns 200 OK
- [ ] Signal API returns well-formed JSON
- [ ] Database stores signals correctly
- [ ] E2E integration: Python → Go → PostgreSQL → API

## Next Steps

1. Port F5 NLP classifier to Go
2. Add authentication/authorization to API
3. Implement webhook delivery
4. Add observability (logs, metrics, traces)
5. Kubernetes manifests for production deployment

## Rollback

If anything goes wrong, switch back to Python:
```bash
git checkout main
# Python pipeline continues from git history
```

---

**Status**: Phase 1 in progress  
**Last Updated**: May 26, 2026  
**Owner**: Ganji Protocol Development Team
