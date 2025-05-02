import React from 'react';

interface EnrichmentResult {
  source: string;
  pValue: number;
  enrichmentScore: number;
  genes: string[];
}

interface EnrichmentAnalysisProps {
  results: EnrichmentResult[];
}

export function EnrichmentAnalysis({ results }: EnrichmentAnalysisProps) {
  return (
    <div className="space-y-4">
      {results.map((result, index) => (
        <div
          key={index}
          className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700"
        >
          <h3 className="text-lg font-semibold mb-2">{result.source}</h3>
          <div className="space-y-2">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              p-value: {result.pValue.toExponential(2)}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Enrichment Score: {result.enrichmentScore.toFixed(2)}
            </p>
            <div className="mt-3">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Enriched Genes:
              </p>
              <div className="flex flex-wrap gap-2">
                {result.genes.map((gene, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 rounded text-sm"
                  >
                    {gene}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}