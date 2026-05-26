package main

import (
	"fmt"
	"log"
	"net/http"
	"os"

	"github.com/go-chi/chi/v5"
	"github.com/vektasafe/ganji-protocol/go-service/pkg/api"
	"github.com/vektasafe/ganji-protocol/go-service/pkg/storage"
)

func main() {
	// Database connection
	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		dbURL = "postgres://ganji:ganji@localhost:5432/ganji_protocol"
	}

	db, err := storage.NewDatabase(dbURL)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer db.Close()

	log.Println("Connected to PostgreSQL")

	// Router
	r := chi.NewRouter()

	// Health check
	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `{"status":"ok","service":"ganji-service"}`)
	})

	// API endpoints
	handler := api.NewHandler(db)
	r.Post("/api/v1/score", handler.ComputeScore)
	r.Get("/api/v1/signal/latest", handler.GetLatestSignal)
	r.Get("/api/v1/signal/archive", handler.GetSignalArchive)

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("Ganji Protocol service starting on :%s", port)
	if err := http.ListenAndServe(":"+port, r); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}
