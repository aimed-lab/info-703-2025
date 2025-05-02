import React, { useEffect, useState } from 'react';
import { X, Loader2, Info } from 'lucide-react';

interface DiseaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  efoId: string;
}

interface DiseaseInfo {
  name: string;
  drugs: Array<{
    name: string;
    target: string;
  }>;
}

interface DrugStructure {
  smiles: string | null;
  iupac: string | null;
}

function capitalizeGene(str: string): string {
  return str.toUpperCase();
}

function capitalizeWords(str: string): string {
  return str.split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ');
}

async function fetchDrugStructure(drugName: string): Promise<DrugStructure> {
  try {
    // First get the CID from the compound name
    const searchResponse = await fetch(
      `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/${encodeURIComponent(drugName)}/property/IUPACName,CanonicalSMILES/JSON`
    );
    
    if (!searchResponse.ok) {
      throw new Error('Failed to fetch drug structure');
    }

    const data = await searchResponse.json();
    return {
      smiles: data.PropertyTable.Properties[0]?.CanonicalSMILES || null,
      iupac: data.PropertyTable.Properties[0]?.IUPACName || null
    };
  } catch (error) {
    console.error('Error fetching drug structure:', error);
    return { smiles: null, iupac: null };
  }
}

async function fetchDiseaseInfo(efoId: string): Promise<DiseaseInfo | null> {
  const OPENTARGETS_API = 'https://api.platform.opentargets.org/api/v4/graphql';
  
  try {
    const response = await fetch(OPENTARGETS_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: `
          query GetDrugsByDisease($efoId: String!) {
            disease(efoId: $efoId) {
              name
              associatedTargets {
                rows {
                  target {
                    approvedSymbol
                    knownDrugs {
                      rows {
                        drug {
                          name
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        `,
        variables: { efoId }
      })
    });

    if (!response.ok) {
      throw new Error('Network response was not ok');
    }

    const data = await response.json();
    
    if (!data.data?.disease) {
      throw new Error('No disease data found');
    }

    // Process the response following the example structure
    const rows = data.data.disease.associatedTargets?.rows || [];
    const uniqueDrugs = new Map<string, { name: string; target: string }>();

    rows.forEach((row: any) => {
      const targetSymbol = capitalizeGene(row.target.approvedSymbol);
      row.target.knownDrugs?.rows?.forEach((drugRow: any) => {
        if (drugRow.drug.name && !uniqueDrugs.has(drugRow.drug.name)) {
          uniqueDrugs.set(drugRow.drug.name, {
            name: capitalizeWords(drugRow.drug.name),
            target: targetSymbol
          });
        }
      });
    });

    // Take only the first 5 unique drugs
    const drugs = Array.from(uniqueDrugs.values()).slice(0, 5);

    return {
      name: capitalizeWords(data.data.disease.name),
      drugs: drugs
    };
  } catch (error) {
    console.error('Error fetching disease info:', error);
    throw error;
  }
}

export function DiseaseModal({ isOpen, onClose, efoId }: DiseaseModalProps) {
  const [diseaseInfo, setDiseaseInfo] = useState<DiseaseInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDrug, setSelectedDrug] = useState<string | null>(null);
  const [drugStructure, setDrugStructure] = useState<DrugStructure | null>(null);
  const [structureLoading, setStructureLoading] = useState(false);

  useEffect(() => {
    if (isOpen && efoId) {
      setLoading(true);
      setError(null);
      setSelectedDrug(null);
      setDrugStructure(null);
      fetchDiseaseInfo(efoId)
        .then(info => {
          setDiseaseInfo(info);
        })
        .catch((err) => {
          console.error('Error:', err);
          setError(err instanceof Error ? err.message : 'Failed to load disease information');
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setDiseaseInfo(null);
      setError(null);
      setSelectedDrug(null);
      setDrugStructure(null);
    }
  }, [isOpen, efoId]);

  useEffect(() => {
    if (selectedDrug) {
      setStructureLoading(true);
      setDrugStructure(null);
      fetchDrugStructure(selectedDrug)
        .then(structure => {
          setDrugStructure(structure);
        })
        .catch(error => {
          console.error('Error fetching drug structure:', error);
        })
        .finally(() => {
          setStructureLoading(false);
        });
    }
  }, [selectedDrug]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="relative w-[90vw] max-w-6xl bg-white dark:bg-gray-800 rounded-lg shadow-xl">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <X className="h-5 w-5 text-gray-500 dark:text-gray-400" />
        </button>
        
        <div className="p-6">
          <h3 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
            Disease Information
          </h3>
          
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-8 h-8 text-purple-600 dark:text-purple-400 animate-spin" />
            </div>
          ) : error ? (
            <div className="text-red-500 dark:text-red-400 py-4">{error}</div>
          ) : diseaseInfo ? (
            <div className="flex gap-8">
              <div className="flex-1 space-y-4">
                <div>
                  <h4 className="font-medium text-gray-700 dark:text-gray-300">Disease Name</h4>
                  <p className="text-gray-900 dark:text-gray-100">{diseaseInfo.name}</p>
                </div>

                {diseaseInfo.drugs.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-700 dark:text-gray-300">Top 5 Known Drugs</h4>
                    <div className="mt-2 space-y-2">
                      {diseaseInfo.drugs.map((drug, index) => (
                        <div
                          key={index}
                          className={`bg-gray-50 dark:bg-gray-700/50 p-2 rounded flex justify-between items-center cursor-pointer transition-colors ${
                            selectedDrug === drug.name 
                              ? 'ring-2 ring-purple-500 dark:ring-purple-400' 
                              : 'hover:bg-gray-100 dark:hover:bg-gray-600'
                          }`}
                          onClick={() => setSelectedDrug(drug.name)}
                        >
                          <span className="text-gray-900 dark:text-gray-100">{drug.name}</span>
                          <span className="text-sm text-purple-600 dark:text-purple-400">
                            {drug.target}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <a
                    href={`https://platform.opentargets.org/disease/${efoId}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-purple-600 dark:text-purple-400 hover:underline"
                  >
                    View on Open Targets Platform
                  </a>
                </div>
              </div>

              <div className="w-px bg-gray-200 dark:bg-gray-700" />

              <div className="flex-1">
                <div className="space-y-6">
                  <div>
                    <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-4">
                      Chemical Structure
                    </h4>
                    {selectedDrug ? (
                      <div className="bg-white dark:bg-gray-900 rounded-lg p-4 flex items-center justify-center min-h-[300px]">
                        <img
                          src={`https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/${encodeURIComponent(selectedDrug)}/PNG`}
                          alt={`Chemical structure of ${selectedDrug}`}
                          className="max-w-full max-h-[400px] object-contain"
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            target.src = `https://cdn.rcsb.org/images/structures/${selectedDrug.toLowerCase()}_assembly-1.jpeg`;
                          }}
                        />
                      </div>
                    ) : (
                      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-8 flex items-center justify-center min-h-[300px]">
                        <p className="text-gray-500 dark:text-gray-400 text-center">
                          Click on a drug to view its chemical structure
                        </p>
                      </div>
                    )}
                  </div>

                  {selectedDrug && (
                    <div className="space-y-4">
                      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                        <h5 className="font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
                          SMILES Notation
                          <Info className="h-4 w-4 text-gray-400" />
                        </h5>
                        {structureLoading ? (
                          <div className="flex items-center justify-center py-2">
                            <Loader2 className="w-5 h-5 text-purple-600 dark:text-purple-400 animate-spin" />
                          </div>
                        ) : drugStructure?.smiles ? (
                          <div className="font-mono text-sm break-all text-gray-600 dark:text-gray-300">
                            {drugStructure.smiles}
                          </div>
                        ) : (
                          <p className="text-gray-500 dark:text-gray-400 text-sm italic">
                            SMILES notation not available
                          </p>
                        )}
                      </div>

                      {drugStructure?.iupac && (
                        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                          <h5 className="font-medium text-gray-700 dark:text-gray-300 mb-2">
                            IUPAC Name
                          </h5>
                          <p className="text-sm text-gray-600 dark:text-gray-300">
                            {drugStructure.iupac}
                          </p>
                        </div>
                      )}

                      <div className="flex justify-center pt-2">
                        <a
                          href={`https://pubchem.ncbi.nlm.nih.gov/compound/${encodeURIComponent(selectedDrug)}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-purple-600 dark:text-purple-400 hover:underline"
                        >
                          View on PubChem
                        </a>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-gray-500 dark:text-gray-400 py-4">
              No disease information available
            </div>
          )}
        </div>
      </div>
    </div>
  );
}