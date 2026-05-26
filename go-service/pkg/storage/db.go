package storage

import (
	"database/sql"
	_ "github.com/lib/pq"
)

// Database wraps the PostgreSQL connection.
type Database struct {
	conn *sql.DB
}

// NewDatabase creates a new database connection.
func NewDatabase(dsn string) (*Database, error) {
	conn, err := sql.Open("postgres", dsn)
	if err != nil {
		return nil, err
	}

	if err := conn.Ping(); err != nil {
		return nil, err
	}

	return &Database{conn: conn}, nil
}

// Close closes the database connection.
func (db *Database) Close() error {
	return db.conn.Close()
}

// Conn returns the underlying SQL connection for queries.
func (db *Database) Conn() *sql.DB {
	return db.conn
}
