import axios from 'axios';
import { jStat } from 'jstat';
import { openai } from '../openai';

interface AnalysisInput {
  query?: string;
  genes?: string[];
  suggestedDiseases?: string[];
  paperSummary?: string;
}

interface GeneSet {
  genes: string[];
  source: string;
}

interface DiseaseGeneAssociation {
  disease: string;
  genes: string[];
  score: number;
}

interface GeneDetails {
  symbol: string;
  name: string;
  ensemblId: string;
  score: number;
  associatedDiseases: Array<{
    name: string;
    score: number;
    efoId?: string;
  }>;
}

export async function analyzeGeneDisease(input: AnalysisInput) {
  try {
    let genes: string[] = [];
    let diseaseAssociations: DiseaseGeneAssociation[] = [];
    let diseaseName = input.query || '';
    let geneDetails: GeneDetails[] = [];

    // Handle input genes from PDF extraction
    if (input.genes && input.genes.length > 0) {
      genes = input.genes;
      
      // Fetch gene details for extracted genes
      const genePromises = genes.map(async (gene) => {
        try {
          const details = await fetchGeneDetails(gene);
          return details;
        } catch (error) {
          console.error(`Error fetching details for gene ${gene}:`, error);
          return null;
        }
      });

      const geneResults = await Promise.all(genePromises);
      geneDetails = geneResults
        .filter((result): result is GeneDetails => result !== null)
        .sort((a, b) => b.score - a.score);

      // If we have suggested diseases, fetch gene associations
      if (input.suggestedDiseases && input.suggestedDiseases.length > 0) {
        const diseaseResults = await Promise.all(
          input.suggestedDiseases.map(async disease => {
            const result = await fetchDiseaseGenes(disease);
            const intersection = genes.filter(gene => result.geneSymbols.includes(gene));
            return {
              disease,
              genes: intersection,
              score: calculateAssociationScore(intersection.length, genes.length, result.geneSymbols.length)
            };
          })
        );
        
        diseaseAssociations = diseaseResults
          .filter(assoc => assoc.genes.length > 0)
          .sort((a, b) => b.score - a.score);
      }

      // If we only have genes (no disease query), return gene analysis
      if (!input.query) {
        const geneSets: GeneSet[] = [{ genes, source: 'Analyzed Genes' }];
        const enrichmentResults = performEnrichmentAnalysis(geneSets);
        const clusters = performGeneClustering(genes);
        const networkData = generateNetworkData(clusters, enrichmentResults, []);
        
        const explanation = await generateExplanation(genes, '', [], enrichmentResults);

        // Format disease associations with scores and EFO IDs
        const formattedDiseases = geneDetails.map(g => {
          const diseases = g.associatedDiseases || [];
          const avgScore = diseases.reduce((sum, d) => sum + d.score, 0) / (diseases.length || 1);
          const formattedList = diseases
            .map(d => `${d.name}${d.efoId ? ` [${d.efoId}]` : ''} [${d.score.toFixed(3)}]`)
            .join(', ');
          const ensemblLink = g.ensemblId ? 
            `<a href="https://ensembl.org/Homo_sapiens/Gene/Summary?g=${g.ensemblId}" target="_blank" rel="noopener noreferrer">${g.ensemblId}</a>` :
            'N/A';
          return [
            g.symbol,
            g.name,
            ensemblLink,
            avgScore.toFixed(3),
            formattedList || 'No disease associations found'
          ];
        });
        
        return {
          enrichmentResults,
          clusters,
          networkData,
          diseaseAssociations: [],
          explanation,
          paperSummary: input.paperSummary,
          tableData: {
            headers: ['Gene Symbol', 'Gene Name', 'Ensembl ID', 'Avg. Association Score', 'Top Associated Diseases [EFO ID] [Score]'],
            rows: formattedDiseases,
            caption: 'Gene Details'
          }
        };
      }
    }

    // Handle disease query if present
    if (input.query) {
      const queryResult = await fetchDiseaseGenes(input.query);
      
      if (genes.length > 0) {
        // If we have input genes, find intersection with disease genes
        const intersection = genes.filter(gene => queryResult.geneSymbols.includes(gene));
        
        if (intersection.length === 0) {
          const formattedDiseases = geneDetails.map(g => {
            const diseases = g.associatedDiseases || [];
            const avgScore = diseases.reduce((sum, d) => sum + d.score, 0) / (diseases.length || 1);
            const formattedList = diseases
              .map(d => `${d.name}${d.efoId ? ` [${d.efoId}]` : ''} [${d.score.toFixed(3)}]`)
              .join(', ');
            const ensemblLink = g.ensemblId ? 
              `<a href="https://ensembl.org/Homo_sapiens/Gene/Summary?g=${g.ensemblId}" target="_blank" rel="noopener noreferrer">${g.ensemblId}</a>` :
              'N/A';
            return [
              g.symbol,
              g.name,
              ensemblLink,
              avgScore.toFixed(3),
              formattedList || 'No disease associations found'
            ];
          });

          return {
            enrichmentResults: [],
            clusters: [],
            networkData: [],
            diseaseAssociations,
            explanation: `No direct gene associations were found between the extracted genes and ${input.query}.`,
            paperSummary: input.paperSummary,
            tableData: {
              headers: ['Gene Symbol', 'Gene Name', 'Ensembl ID', 'Avg. Association Score', 'Top Associated Diseases [EFO ID] [Score]'],
              rows: formattedDiseases,
              caption: `Gene Details for Extracted Genes`
            }
          };
        }
        
        genes = intersection;
        geneDetails = queryResult.geneDetails.filter(g => intersection.includes(g.symbol));
      } else {
        // If we only have disease query, use its genes and details
        genes = queryResult.geneSymbols;
        geneDetails = queryResult.geneDetails;
      }
    }

    if (!genes || genes.length === 0) {
      return {
        enrichmentResults: [],
        clusters: [],
        networkData: [],
        diseaseAssociations: [],
        explanation: 'No genes were found for analysis.',
        paperSummary: input.paperSummary
      };
    }

    // Create gene sets for analysis
    const geneSets: GeneSet[] = [
      { genes, source: diseaseName || 'Analyzed Genes' }
    ];
    
    // Add disease associations as gene sets
    diseaseAssociations.forEach(assoc => {
      if (assoc.genes.length > 0) {
        geneSets.push({
          genes: assoc.genes,
          source: `${assoc.disease} Associated Genes`
        });
      }
    });
    
    // Perform enrichment analysis
    const enrichmentResults = performEnrichmentAnalysis(geneSets);
    
    // Perform gene clustering
    const clusters = performGeneClustering(genes);
    
    // Generate network visualization data
    const networkData = generateNetworkData(clusters, enrichmentResults, diseaseAssociations);
    
    // Get focused explanation of gene-disease relationships
    const explanation = await generateExplanation(
      genes,
      diseaseName,
      diseaseAssociations,
      enrichmentResults
    );

    // Format disease associations with scores and EFO IDs
    const formattedDiseases = geneDetails.map(g => {
      const diseases = g.associatedDiseases || [];
      const avgScore = diseases.reduce((sum, d) => sum + d.score, 0) / (diseases.length || 1);
      const formattedList = diseases
        .map(d => `${d.name}${d.efoId ? ` [${d.efoId}]` : ''} [${d.score.toFixed(3)}]`)
        .join(', ');
      const ensemblLink = g.ensemblId ? 
        `<a href="https://ensembl.org/Homo_sapiens/Gene/Summary?g=${g.ensemblId}" target="_blank" rel="noopener noreferrer">${g.ensemblId}</a>` :
        'N/A';
      return [
        g.symbol,
        g.name,
        ensemblLink,
        avgScore.toFixed(3),
        formattedList || 'No disease associations found'
      ];
    });
    
    return {
      enrichmentResults,
      clusters,
      networkData,
      diseaseAssociations,
      explanation,
      paperSummary: input.paperSummary,
      tableData: geneDetails.length > 0 ? {
        headers: ['Gene Symbol', 'Gene Name', 'Ensembl ID', 'Avg. Association Score', 'Top Associated Diseases [EFO ID] [Score]'],
        rows: formattedDiseases,
        caption: diseaseName ? `Gene Associations for ${diseaseName}` : 'Gene Details'
      } : undefined
    };
  } catch (error: any) {
    console.error('Error in gene-disease analysis:', error);
    throw new Error(error.message || 'Failed to analyze gene-disease relationships');
  }
}

function validateGeneSymbol(gene: string): boolean {
  const genePattern = /^[A-Za-z][A-Za-z0-9\-]{0,19}$/;
  return genePattern.test(gene);
}

async function fetchGeneDetails(gene: string): Promise<GeneDetails | null> {
  if (!validateGeneSymbol(gene)) {
    console.warn(`Invalid gene symbol format: ${gene}`);
    return null;
  }

  const OPENTARGETS_API = 'https://api.platform.opentargets.org/api/v4/graphql';
  
  try {
    // First search for the gene
    const searchResponse = await axios.post<{ data: any }>(OPENTARGETS_API, {
      query: `
        query searchTarget($queryString: String!) {
          search(queryString: $queryString, entityNames: ["target"]) {
            hits {
              id
              object {
                ... on Target {
                  id
                  approvedSymbol
                  approvedName
                }
              }
            }
          }
        }
      `,
      variables: { queryString: gene }
    });

    const target = searchResponse.data?.data?.search?.hits?.[0]?.object;
    
    if (!target?.id) {
      return null;
    }

    // Then fetch associated diseases
    const diseaseResponse = await axios.post<{ data: any }>(OPENTARGETS_API, {
      query: `
        query targetDiseases($targetId: String!) {
          target(ensemblId: $targetId) {
            id
            approvedSymbol
            approvedName
            associatedDiseases(page: { index: 0, size: 5 }) {
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
      `,
      variables: { targetId: target.id }
    });

    const targetData = diseaseResponse.data?.data?.target;
    const associatedDiseases = targetData?.associatedDiseases?.rows?.map(row => ({
      name: row.disease.name,
      score: row.score,
      efoId: row.disease.id
    })) || [];

    return {
      symbol: targetData?.approvedSymbol || gene,
      name: targetData?.approvedName || '',
      ensemblId: target.id,
      score: associatedDiseases.reduce((sum, d) => sum + d.score, 0) / (associatedDiseases.length || 1),
      associatedDiseases
    };
  } catch (error: any) {
    if (axios.isAxiosError(error)) {
      const statusCode = error.response?.status;
      const errorMessage = error.response?.data?.errors?.[0]?.message || error.message;
      
      console.error(`OpenTargets API error (${statusCode}):`, errorMessage);
      
      if (statusCode === 429) {
        throw new Error('Rate limit exceeded. Please try again later.');
      }
    }
    
    console.error('Error fetching gene details:', error);
    return null;
  }
}

function calculateAssociationScore(
  intersectionSize: number,
  inputGeneCount: number,
  diseaseGeneCount: number
): number {
  if (intersectionSize === 0) return 0;
  
  const union = inputGeneCount + diseaseGeneCount - intersectionSize;
  const jaccard = intersectionSize / union;
  
  const totalGenes = 20000;
  const pValue = 1 - jStat.hypgeom.cdf(
    intersectionSize - 1,
    totalGenes,
    diseaseGeneCount,
    inputGeneCount
  );
  
  return (jaccard * 0.4 + (1 - pValue) * 0.6);
}

async function fetchDiseaseGenes(query: string): Promise<{ geneSymbols: string[], geneDetails: GeneDetails[] }> {
  const OPENTARGETS_API = 'https://api.platform.opentargets.org/api/v4/graphql';
  
  try {
    // First try to search for the disease
    const searchResponse = await axios.post<{ data: any }>(OPENTARGETS_API, {
      query: `
        query searchDisease($queryString: String!) {
          search(queryString: $queryString, entityNames: ["disease"]) {
            hits {
              id
              name
              entity
            }
          }
        }
      `,
      variables: { queryString: query }
    });

    const diseaseId = searchResponse.data?.data?.search?.hits?.[0]?.id;
    
    if (!diseaseId) {
      return { geneSymbols: [], geneDetails: [] };
    }

    // Then fetch associated genes using the disease ID
    const response = await axios.post<{ data: any }>(OPENTARGETS_API, {
      query: `
        query diseaseAssociations($efoId: String!) {
          disease(efoId: $efoId) {
            id
            name
            associatedTargets(page: { index: 0, size: 100 }) {
              rows {
                target {
                  id
                  approvedSymbol
                  approvedName
                }
                score
              }
            }
          }
        }
      `,
      variables: { efoId: diseaseId }
    });

    const rows = response.data?.data?.disease?.associatedTargets?.rows || [];
    const geneDetails = rows
      .filter((row: any) => row.target && row.target.approvedSymbol)
      .map((row: any) => ({
        symbol: row.target.approvedSymbol,
        name: row.target.approvedName || '',
        ensemblId: row.target.id,
        score: row.score || 0,
        associatedDiseases: [{
          name: response.data?.data?.disease?.name || '',
          score: row.score || 0,
          efoId: response.data?.data?.disease?.id
        }]
      }));

    // Fetch associated diseases for each gene
    const geneDetailsWithDiseases = await Promise.all(
      geneDetails.map(async (gene) => {
        try {
          const details = await fetchGeneDetails(gene.symbol);
          return {
            ...gene,
            associatedDiseases: details?.associatedDiseases || gene.associatedDiseases
          };
        } catch (error) {
          console.error(`Error fetching diseases for gene ${gene.symbol}:`, error);
          return gene;
        }
      })
    );

    return {
      geneSymbols: geneDetailsWithDiseases.map(g => g.symbol),
      geneDetails: geneDetailsWithDiseases
    };
  } catch (error: any) {
    console.error('Error fetching from OpenTargets:', error);
    return { geneSymbols: [], geneDetails: [] };
  }
}

function performEnrichmentAnalysis(geneSets: GeneSet[]) {
  return geneSets.map(set => ({
    source: set.source,
    pValue: calculateEnrichmentPValue(set.genes),
    enrichmentScore: Math.log2(set.genes.length + 1),
    genes: set.genes
  }));
}

function calculateEnrichmentPValue(genes: string[]): number {
  const totalGenes = 20000;
  const setSize = genes.length;
  const backgroundSize = 1000;
  
  return 1 - jStat.hypgeom.cdf(
    setSize - 1,
    totalGenes,
    backgroundSize,
    setSize
  );
}

function performGeneClustering(genes: string[]) {
  const clusters: string[][] = [];
  const remainingGenes = [...genes];
  
  while (remainingGenes.length > 0) {
    const currentGene = remainingGenes.shift()!;
    const cluster = [currentGene];
    
    const prefix = currentGene.substring(0, 2);
    let i = 0;
    while (i < remainingGenes.length) {
      if (remainingGenes[i].startsWith(prefix)) {
        cluster.push(remainingGenes[i]);
        remainingGenes.splice(i, 1);
      } else {
        i++;
      }
    }
    
    clusters.push(cluster);
  }
  
  return clusters;
}

function generateNetworkData(
  clusters: string[][],
  enrichmentResults: any[],
  diseaseAssociations: DiseaseGeneAssociation[]
) {
  const elements = [];
  const processedEdges = new Set();
  
  diseaseAssociations.forEach(association => {
    elements.push({
      data: {
        id: `disease-${association.disease}`,
        label: association.disease,
        type: 'disease',
        color: '#e11d48'
      }
    });
  });

  clusters.forEach((cluster, clusterIndex) => {
    cluster.forEach(gene => {
      elements.push({
        data: {
          id: gene,
          label: gene,
          type: 'gene',
          cluster: clusterIndex,
          color: `hsl(${200 + (clusterIndex * 30) % 160}, 70%, 50%)`
        }
      });
      
      cluster.forEach(otherGene => {
        if (gene !== otherGene) {
          const edgeId = [gene, otherGene].sort().join('_');
          if (!processedEdges.has(edgeId)) {
            elements.push({
              data: {
                id: edgeId,
                source: gene,
                target: otherGene,
                type: 'cluster',
                weight: 1
              }
            });
            processedEdges.add(edgeId);
          }
        }
      });
    });
  });
  
  diseaseAssociations.forEach(association => {
    association.genes.forEach(gene => {
      const edgeId = `disease-${association.disease}_${gene}`;
      if (!processedEdges.has(edgeId)) {
        elements.push({
          data: {
            id: edgeId,
            source: `disease-${association.disease}`,
            target: gene,
            type: 'disease-gene',
            weight: association.score * 2
          }
        });
        processedEdges.add(edgeId);
      }
    });
  });
  
  return elements;
}

async function generateExplanation(
  genes: string[],
  diseaseName: string,
  diseaseAssociations: DiseaseGeneAssociation[],
  enrichmentResults: any[]
) {
  try {
    const focusedContent = diseaseName
      ? `Focus on analyzing the relationship between these genes and ${diseaseName}.`
      : 'Analyze the relationships between these genes and their associated functions.';

    const completion = await openai.chat.completions.create({
      model: "gpt-4-turbo-preview",
      messages: [
        {
          role: "system",
          content: `You are a biomedical research expert. ${focusedContent}

Rules:
1. Write in plain text without any markdown formatting
2. Do not use special characters like *, #, or -
3. Do not use headings or section markers
4. Use clear paragraph breaks for different sections
5. Present information in a clear, narrative format
6. Avoid technical jargon when possible
7. Focus on direct relationships and evidence
8. Complete all analysis without truncation
9. Use simple formatting with just paragraphs and spacing

Required information to cover:
1. Overview of the identified genes
2. Disease associations (if specified)
3. Statistical significance
4. Key relationships between genes and diseases`
        },
        {
          role: "user",
          content: `Analyze these gene-disease relationships:

Genes: ${JSON.stringify(genes)}
${diseaseName ? `Disease: ${diseaseName}` : ''}
Disease Associations: ${JSON.stringify(diseaseAssociations)}
Enrichment Results: ${JSON.stringify(enrichmentResults)}

Provide a complete analysis focusing on ${diseaseName ? `the relationship between these genes and ${diseaseName}` : 'the relationships between these genes'}.`
        }
      ],
      temperature: 0.1,
      max_tokens: 2000
    });

    return completion.choices[0]?.message?.content || 
      "Unable to generate explanation for the analysis results.";
  } catch (error: any) {
    console.error('Error generating explanation:', error);
    return "An error occurred while generating the explanation.";
  }
}

export {
  searchKnowledgeBase,
  clearData,
  getLoadedFiles,
  loadBackendData,
  processCsvFile,
  processFile
};