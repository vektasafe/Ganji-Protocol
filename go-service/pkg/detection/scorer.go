package detection

import (
	"log"
	"math"
)

// CIPSWeights from config
var CIPSWeights = map[string]int{
	"z_score_low":              1,
	"z_score_high":             1,
	"cpii":                     3,
	"gvci":                     2,
	"rss":                      2,
	"nlp_intervention_imminent": 2,
	"nlp_hawkish":              1,
	"nlp_neutral":              0,
	"nlp_dovish":               -1,
	"bpps":                     1,
}

const (
	ZScoreThresholdLow    = 2.0
	ZScoreThresholdHigh   = 2.5
	CIPSHighThreshold     = 5
	CIPSMediumThreshold   = 3
	CIPSLowThreshold      = 1
	GVCISuppressionThreshold = 0.3
)

// ComputeCIPS computes the CBK Intervention Probability Score from feature inputs.
func ComputeCIPS(features FeatureInput) DetectionResult {
	score := 0
	components := make(map[string]int)
	details := make(map[string]float64)

	// F1: Z-score
	if features.F1ZScoreFired {
		absZ := math.Abs(features.F1ZScore)
		if absZ > ZScoreThresholdLow {
			score += CIPSWeights["z_score_low"]
			components["z_score_low"] = CIPSWeights["z_score_low"]
		}
		if absZ > ZScoreThresholdHigh {
			score += CIPSWeights["z_score_high"]
			components["z_score_high"] = CIPSWeights["z_score_high"]
		}
		details["z_score"] = features.F1ZScore
	}

	// F2: CPII
	cpiiContributed := false
	if features.F2CPIIFired {
		score += CIPSWeights["cpii"]
		components["cpii"] = CIPSWeights["cpii"]
		cpiiContributed = true
		details["cpii"] = features.F2CPIIValue
	}

	// F3: GVCI
	if features.F3GVCIFired {
		score += CIPSWeights["gvci"]
		components["gvci"] = CIPSWeights["gvci"]
		details["gvci"] = features.F3GVCIValue
	}

	// F4: RSS (Phase 2 - typically not fired yet)
	if features.F4RSSFired {
		score += CIPSWeights["rss"]
		components["rss"] = CIPSWeights["rss"]
	}

	// F5: NLP tone
	toneToCIPS := map[string]int{
		"INTERVENTION_IMMINENT": 2,
		"HAWKISH":               1,
		"NEUTRAL":               0,
		"DOVISH":                -1,
	}
	nlpScore := toneToCIPS[features.F5NLPTone]
	if nlpScore != 0 || features.F5NLPTone != "" {
		score += nlpScore
		components["nlp_"+features.F5NLPTone] = nlpScore
	}

	// F6: BPPS
	if features.F6BPPSFired {
		score += CIPSWeights["bpps"]
		components["bpps"] = CIPSWeights["bpps"]
		details["bpps_premium"] = features.F6BPPSPremium
	}

	// Determine confidence tier (raw)
	confidenceRaw := "NONE"
	if score >= CIPSHighThreshold {
		confidenceRaw = "HIGH"
	} else if score >= CIPSMediumThreshold {
		confidenceRaw = "MEDIUM"
	} else if score >= CIPSLowThreshold {
		confidenceRaw = "LOW"
	}

	// Calendar adjustment: downgrade one tier during high-impact events
	confidence := confidenceRaw
	highImpactFlags := map[string]bool{"BUDGET_MONTH": true, "IMF_REVIEW_MONTH": true}
	for _, flag := range features.F7CalendarFlags {
		if highImpactFlags[flag] {
			tierMap := map[string]string{
				"HIGH":   "MEDIUM",
				"MEDIUM": "LOW",
				"LOW":    "NONE",
				"NONE":   "NONE",
			}
			confidence = tierMap[confidenceRaw]
			log.Printf("Calendar adjustment: %s -> %s (%v)", confidenceRaw, confidence, features.F7CalendarFlags)
			break
		}
	}

	// Direction classification
	direction := classifyDirection(features)

	// Sequence pattern
	sequencePattern := features.F3GVCIValue < GVCISuppressionThreshold && features.F1ZScoreFired

	log.Printf("CIPS: score=%d | confidence=%s (raw=%s) | direction=%s | sequence=%v",
		score, confidence, confidenceRaw, direction, sequencePattern)

	return DetectionResult{
		CIPSScore:       score,
		Confidence:      confidence,
		ConfidenceRaw:   confidenceRaw,
		Direction:       direction,
		SequencePattern: sequencePattern,
		CPIIContributed: cpiiContributed,
		CalendarFlags:   features.F7CalendarFlags,
		Components:      components,
		Details:         details,
	}
}

// classifyDirection determines KES_SUPPORT or KES_FLOOR_DEFENCE
func classifyDirection(features FeatureInput) string {
	z := features.F1ZScore

	if z > ZScoreThresholdLow && !features.F6CBKSuppression {
		return "KES_SUPPORT"
	} else if z < -ZScoreThresholdLow || features.F6CBKSuppression {
		return "KES_FLOOR_DEFENCE"
	}
	return "INDETERMINATE"
}
