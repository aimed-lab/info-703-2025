import React from 'react';

interface GeneClusterProps {
  cluster: string[];
  index: number;
}

export function GeneCluster({ cluster, index }: GeneClusterProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
      <h3 className="text-lg font-semibold mb-2">Cluster {index + 1}</h3>
      <div className="flex flex-wrap gap-2">
        {cluster.map((gene, i) => (
          <span
            key={i}
            className="px-3 py-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 rounded-full text-sm"
          >
            {gene}
          </span>
        ))}
      </div>
    </div>
  );
}