import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';
import cola from 'cytoscape-cola';
import { FileText, Network, Database, Search, Brain, Download } from 'lucide-react';
import { analyzeGeneDisease } from '../../lib/biomedical/analysis';
import { processFile } from '../../lib/biomedical/fileProcessing';
import { GeneCluster } from './GeneCluster';
import { EnrichmentAnalysis } from './EnrichmentAnalysis';
import { SearchInterface } from './SearchInterface';
import { ResultsViewer } from './ResultsViewer';
import { LoadingState } from './LoadingState';
import { ErrorBoundary } from './ErrorBoundary';

// Register the cola layout
cytoscape.use(cola);

interface BiomedicalModuleProps {
  onTransferToChat?: () => void;
}

export function BiomedicalModule({ onTransferToChat }: BiomedicalModuleProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<any>(null);
  const [networkData, setNetworkData] = useState<any>(null);
  const [extractedGenes, setExtractedGenes] = useState<string[]>([]);
  const [suggestedDiseases, setSuggestedDiseases] = useState<string[]>([]);
  const cyRef = useRef<any>(null);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const processedData = await Promise.all(
        acceptedFiles.map(file => processFile(file))
      );
      
      const allGenes = [...new Set(processedData.flatMap(data => data.genes))];
      const allDiseases = [...new Set(processedData.flatMap(data => data.suggestedDiseases))];
      const paperSummary = processedData[0]?.summary; // Get the summary from the first file
      
      setExtractedGenes(allGenes);
      setSuggestedDiseases(allDiseases);
      
      if (allGenes.length > 0) {
        const analysisResults = await analyzeGeneDisease({ 
          genes: allGenes,
          suggestedDiseases: allDiseases,
          paperSummary // Pass the summary to the analysis
        });
        setResults(analysisResults);
        if (analysisResults.networkData && Array.isArray(analysisResults.networkData)) {
          setNetworkData(analysisResults.networkData);
        }
      } else {
        setError('No genes were found in the uploaded files');
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred processing the files');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
    },
    multiple: true
  });

  const handleSearch = async (query: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const searchResults = await analyzeGeneDisease({ query });
      setResults(searchResults);
      if (searchResults.networkData && Array.isArray(searchResults.networkData)) {
        setNetworkData(searchResults.networkData);
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred during search');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ErrorBoundary>
      <div className="min-h-full bg-gradient-to-b from-purple-50 to-white dark:from-gray-900 dark:to-gray-800">
        <div className="max-w-[95%] mx-auto px-4 py-8">
          <div className="space-y-6">
            {/* Input Section */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
              <h2 className="text-2xl font-semibold mb-4 flex items-center gap-2">
                <FileText className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                Document Upload
              </h2>
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  isDragActive
                    ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
                    : 'border-gray-300 dark:border-gray-600'
                }`}
              >
                <input {...getInputProps()} />
                <p className="text-gray-600 dark:text-gray-300">
                  Drag & drop PDF or text files here, or click to select files
                </p>
              </div>

              {extractedGenes.length > 0 && (
                <div className="mt-4">
                  <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Extracted Genes:
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {extractedGenes.map((gene, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 rounded text-sm"
                      >
                        {gene}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {suggestedDiseases.length > 0 && (
                <div className="mt-4">
                  <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Suggested Diseases:
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {suggestedDiseases.map((disease, index) => (
                      <button
                        key={index}
                        onClick={() => handleSearch(disease)}
                        className="px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full text-sm hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
                      >
                        {disease}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <SearchInterface onSearch={handleSearch} />
            
            {isLoading && <LoadingState />}
            
            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 p-4 rounded-lg">
                {error}
              </div>
            )}

            {/* Results Section */}
            {results && (
              <div className="space-y-6">
                <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-2xl font-semibold flex items-center gap-2">
                      <Network className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                      Analysis Results
                    </h2>
                  </div>
                  
                  <ResultsViewer 
                    results={results}
                    onTransferToChat={onTransferToChat}
                  />
                </div>

                {networkData && Array.isArray(networkData) && networkData.length > 0 && (
                  <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
                    <h3 className="text-xl font-semibold mb-4">Network Visualization</h3>
                    <div className="h-[500px] border rounded-lg overflow-hidden">
                      <CytoscapeComponent
                        elements={networkData}
                        style={{ width: '100%', height: '100%' }}
                        cy={(cy) => { cyRef.current = cy; }}
                        layout={{
                          name: 'cola',
                          nodeSpacing: 80,
                          edgeLength: 120,
                          animate: true,
                          maxSimulationTime: 2000,
                          refresh: 1,
                          randomize: true
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
                              'text-max-width': '100px'
                            }
                          },
                          {
                            selector: 'node[type="disease"]',
                            style: {
                              'shape': 'diamond',
                              'width': 50,
                              'height': 50,
                              'font-weight': 'bold',
                              'font-size': '14px'
                            }
                          },
                          {
                            selector: 'node[type="gene"]',
                            style: {
                              'shape': 'ellipse',
                              'width': 40,
                              'height': 40
                            }
                          },
                          {
                            selector: 'edge',
                            style: {
                              'width': 'data(weight)',
                              'line-color': '#9333ea',
                              'opacity': 0.6,
                              'curve-style': 'bezier'
                            }
                          },
                          {
                            selector: 'edge[type="cluster"]',
                            style: {
                              'line-style': 'solid',
                              'line-color': '#6366f1',
                              'width': 2
                            }
                          },
                          {
                            selector: 'edge[type="disease-gene"]',
                            style: {
                              'line-style': 'dashed',
                              'line-color': '#e11d48',
                              'width': 'data(weight)'
                            }
                          }
                        ]}
                      />
                    </div>
                    <div className="mt-4 space-y-2">
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Network Legend:
                      </p>
                      <div className="flex flex-wrap gap-4">
                        <div className="flex items-center gap-2">
                          <div className="w-4 h-4 rounded-full bg-[#6366f1]" />
                          <span className="text-sm">Genes (colored by cluster)</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-4 h-4 rotate-45 bg-[#e11d48]" />
                          <span className="text-sm">Diseases</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-0.5 bg-[#6366f1]" />
                          <span className="text-sm">Gene cluster relationship</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-0.5 border-t-2 border-dashed border-[#e11d48]" />
                          <span className="text-sm">Disease-gene association</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}