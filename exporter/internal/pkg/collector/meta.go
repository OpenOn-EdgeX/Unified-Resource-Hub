// Adapted for Unified Resource Hub. See NOTICE.
package collector

type CollectMeta struct {
	DurationMs float64

	GPUPstate uint32

	DCGMVersion string
}

type MetaProvider interface {
	GetCollectMeta() *CollectMeta
}
