import React, { useEffect, useState, useRef } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';
import cola from 'cytoscape-cola';
import axios from 'axios';
import { Download } from 'lucide-react';
import { saveAs } from 'file-saver';

// Register the cola layout
cytoscape.use(cola);

interface GeneGraphProps {
  ensemblId: string;
  geneName: string;
}

export function GeneGraph({ ensemblId, geneName }: GeneGraphProps) {
  const [elements, setElements] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cyRef = useRef<any>(null);

  const downloadImage = (format: 'png' | 'jpg') => {
    if (cyRef.current) {
      const cy = cyRef.current;
      const imageData = format === 'png' 
        ? cy.png({ full: true, scale: 2, output: 'blob' })
        : cy.jpg({ full: true, quality: 0.95, output: 'blob' });

      saveAs(imageData, `gene-network.${format}`);
    }
  };

  useEffect(() => {
    async function loadGraph() {
      try {
        setLoading(true);
        setError(null);

        const query = `
          query {
            target(ensemblId: "${ensemblId}") {
              id
              approvedSymbol
              knownDrugs {
                rows {
                  drug {
                    id
                    name
                    mechanismsOfAction {
                      rows {
                        actionType
                      }
                    }
                  }
                  disease {
                    id
                    name
                  }
                  phase
                  status
                }
              }
              associatedDiseases {
                rows {
                  disease {
                    id
                    name
                  }
                  score
                }
              }
            }
          }
        `;

        const response = await axios.post(
          'https://api.platform.opentargets.org/api/v4/graphql',
          { query },
          { headers: { 'Content-Type': 'application/json' } }
        );

        const data = response.data.data.target;
        const elements: any[] = [];
        const nodes = new Set();

        // Add gene node
        elements.push({
          data: {
            id: data.approvedSymbol,
            label: data.approvedSymbol,
            type: 'gene',
            color: '#6366f1'
          }
        });
        nodes.add(data.approvedSymbol);

        // Process disease associations
        data.associatedDiseases.rows.forEach(({ disease, score }: any) => {
          if (!nodes.has(disease.id)) {
            nodes.add(disease.id);
            elements.push({
              data: {
                id: disease.id,
                label: disease.name,
                type: 'disease',
                color: '#e11d48'
              }
            });
          }
          elements.push({
            data: {
              source: data.approvedSymbol,
              target: disease.id,
              label: 'associated',
              weight: Math.max(1, score * 5),
              type: 'disease-gene'
            }
          });
        });

        // Process drug associations
        data.knownDrugs.rows.forEach(({ drug, disease, phase }: any) => {
          if (!nodes.has(drug.id)) {
            nodes.add(drug.id);
            elements.push({
              data: {
                id: drug.id,
                label: drug.name,
                type: 'drug',
                color: '#059669'
              }
            });
          }

          if (disease && !nodes.has(disease.id)) {
            nodes.add(disease.id);
            elements.push({
              data: {
                id: disease.id,
                label: disease.name,
                type: 'disease',
                color: '#e11d48'
              }
            });
          }

          // Add drug-gene edge
          elements.push({
            data: {
              source: drug.id,
              target: data.approvedSymbol,
              label: 'targets',
              weight: Math.max(1, phase),
              type: 'drug-gene'
            }
          });

          // Add drug-disease edge if disease exists
          if (disease) {
            elements.push({
              data: {
                source: drug.id,
                target: disease.id,
                label: 'treats',
                weight: Math.max(1, phase),
                type: 'drug-disease'
              }
            });
          }
        });

        setElements(elements);
      } catch (err) {
        console.error('Error loading graph data:', err);
        setError('Failed to load graph data');
      } finally {
        setLoading(false);
      }
    }

    loadGraph();
  }, [ensemblId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[600px] bg-gray-50 dark:bg-gray-900 rounded-lg">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 dark:border-purple-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-[600px] bg-gray-50 dark:bg-gray-900 rounded-lg text-red-500 dark:text-red-400">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2">
        <button
          onClick={() => downloadImage('png')}
          title="Download as PNG"
          className="p-2 text-gray-600 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
        >
          <Download className="h-5 w-5" />
        </button>
      </div>
      
      <div className="h-[600px] bg-white dark:bg-gray-900 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700">
        <CytoscapeComponent
          elements={elements}
          style={{ width: '100%', height: '100%' }}
          cy={(cy) => { cyRef.current = cy; }}
          layout={{
            name: 'cola',
            nodeSpacing: 120,
            edgeLength: 150,
            animate: true,
            maxSimulationTime: 2000,
            refresh: 1,
            randomize: false,
            infinite: false
          }}
          stylesheet={[
            {
              selector: 'node',
              style: {
                'background-color': 'data(color)',
                'label': 'data(label)',
                'color': '#1f2937',
                'font-size': '12px',
                'text-valign': 'center',
                'text-halign': 'center',
                'text-wrap': 'wrap',
                'text-max-width': '100px',
                'padding': '10px'
              }
            },
            {
              selector: 'node[type="disease"]',
              style: {
                'shape': 'diamond',
                'width': 40,
                'height': 40
              }
            },
            {
              selector: 'node[type="drug"]',
              style: {
                'shape': 'round-rectangle',
                'width': 40,
                'height': 40
              }
            },
            {
              selector: 'node[type="gene"]',
              style: {
                'shape': 'ellipse',
                'width': 45,
                'height': 45,
                'font-weight': 'bold',
                'font-size': '14px'
              }
            },
            {
              selector: 'edge',
              style: {
                'width': 'data(weight)',
                'line-color': '#9333ea',
                'target-arrow-color': '#9333ea',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'opacity': 0.7,
                'label': 'data(label)',
                'font-size': '10px',
                'text-rotation': 'autorotate',
                'text-margin-y': '-10px'
              }
            },
            {
              selector: 'edge[type="drug-gene"]',
              style: {
                'line-color': '#059669',
                'target-arrow-color': '#059669'
              }
            },
            {
              selector: 'edge[type="disease-gene"]',
              style: {
                'line-color': '#e11d48',
                'target-arrow-color': '#e11d48',
                'line-style': 'dashed'
              }
            },
            {
              selector: 'edge[type="drug-disease"]',
              style: {
                'line-color': '#6366f1',
                'target-arrow-color': '#6366f1'
              }
            }
          ]}
        />
      </div>
    </div>
  );
}