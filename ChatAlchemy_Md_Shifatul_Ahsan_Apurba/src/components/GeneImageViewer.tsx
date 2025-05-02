import React from 'react';
import { GeneGraph } from './GeneGraph';

function capitalizeGene(str: string): string {
  return str.toUpperCase();
}

interface GeneImageViewerProps {
  ensemblId: string;
  geneName: string;
}

export function GeneImageViewer({ ensemblId, geneName }: GeneImageViewerProps) {
  const capitalizedGeneName = capitalizeGene(geneName);

  return (
    <div className="p-4 space-y-4">
      <div>
        <h3 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
          Gene Interactions: {capitalizedGeneName}
        </h3>
        <GeneGraph ensemblId={ensemblId} geneName={geneName} />
        <div className="mt-4 space-y-2">
          <div className="flex flex-wrap gap-4">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded-full bg-[#6366f1]" />
              <span className="text-sm">Gene</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rotate-45 bg-[#e11d48]" />
              <span className="text-sm">Diseases</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-[#059669]" />
              <span className="text-sm">Drugs</span>
            </div>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Interactive network showing gene-disease-drug relationships. Drag nodes to rearrange, scroll to zoom.
          </p>
          <a 
            href={`https://ensembl.org/Homo_sapiens/Gene/Summary?g=${ensemblId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block text-sm text-purple-600 dark:text-purple-400 hover:underline"
          >
            View full details on Ensembl
          </a>
        </div>
      </div>
    </div>
  );
}