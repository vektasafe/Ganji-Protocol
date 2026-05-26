package detection

// FeatureInput represents the input features for CIPS scoring.
type FeatureInput struct {
	F1ZScore           float64  `json:"f1_zscore"`
	F1ZScoreFired      bool     `json:"f1_zscore_fired"`
	F2CPIIFired        bool     `json:"f2_cpii_fired"`
	F2CPIIValue        float64  `json:"f2_cpii_value"`
	F3GVCIFired        bool     `json:"f3_gvci_fired"`
	F3GVCIValue        float64  `json:"f3_gvci_value"`
	F4RSSFired         bool     `json:"f4_rss_fired"`
	F5NLPTone          string   `json:"f5_nlp_tone"` // NEUTRAL, HAWKISH, DOVISH, INTERVENTION_IMMINENT
	F6BPPSFired        bool     `json:"f6_bpps_fired"`
	F6BPPSPremium      float64  `json:"f6_bpps_premium"`
	F6CBKSuppression   bool     `json:"f6_cbk_suppression"`
	F7CalendarFlags    []string `json:"f7_calendar_flags"`
}

// DetectionResult represents the CIPS scoring output.
type DetectionResult struct {
	CIPSScore          int                `json:"cips_score"`
	Confidence         string             `json:"confidence"` // HIGH, MEDIUM, LOW, NONE
	ConfidenceRaw      string             `json:"confidence_raw"`
	Direction          string             `json:"direction"` // KES_SUPPORT, KES_FLOOR_DEFENCE, INDETERMINATE
	SequencePattern    bool               `json:"sequence_pattern"`
	CPIIContributed    bool               `json:"cpii_contributed"`
	CalendarFlags      []string           `json:"calendar_flags"`
	Components         map[string]int     `json:"components"`
	Details            map[string]float64 `json:"details"`
}

// Signal represents a complete Ganji Protocol signal output.
type Signal struct {
	SignalID         string             `json:"signal_id"`
	Pair             string             `json:"pair"`
	Timestamp        string             `json:"timestamp"`
	DataDate         string             `json:"data_date"`
	PipelineVersion  string             `json:"pipeline_version"`
	Detection        DetectionResult    `json:"detection"`
	Components       map[string]any     `json:"components"`
	Context          map[string]any     `json:"context"`
	SignalContext    string             `json:"signal_context"`
	RegulatoryNote   string             `json:"regulatory_note"`
}
