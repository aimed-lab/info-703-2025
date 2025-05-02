import React, { useState } from 'react';
import { MessageSquare, FileText, Network, Brain, Share, Sparkles, BookOpen, Table } from 'lucide-react';
import { openai } from '../../lib/openai';
import { createNewChat, saveChat, getAllChats } from '../../lib/storage';
import { v4 as uuidv4 } from 'uuid';
import { DataTable } from '../DataTable';

interface ResultsViewerProps {
  results: {
    enrichmentResults: any[];
    clusters: string[][];
    explanation: string;
    paperSummary?: string;
    tableData?: {
      headers: string[];
      rows: any[][];
      caption?: string;
    };
  };
  onTransferToChat?: () => void;
}

export function ResultsViewer({ results, onTransferToChat }: ResultsViewerProps) {
  const [isTransferring, setIsTransferring] = useState(false);

  const generatePromptSuggestions = async (analysisContent: string) => {
    try {
      const completion = await openai.chat.completions.create({
        model: "gpt-4-turbo-preview",
        messages: [
          {
            role: "system",
            content: `You are PharmAlchemy, a pharmaceutical data assistant. Generate 3 short, focused questions about drug development and therapeutic applications based on the analysis content. Each question MUST:

1. Be 10-15 words maximum
2. Focus on drug development or treatment
3. Start with "What drugs..." or "How can..."
4. Be directly related to pharmaceutical applications
5. Be specific and actionable
6. Be relevant to the analyzed genes and diseases

DO NOT:
- Generate general research questions
- Include biological mechanisms
- Make questions too long
- Use complex terminology`
          },
          {
            role: "user",
            content: `Based on this analysis, generate pharmaceutical-focused questions:\n\n${analysisContent}`
          }
        ],
        temperature: 0.7,
        max_tokens: 250
      });

      const suggestions = completion.choices[0]?.message?.content
        ?.split('\n')
        .filter(line => line.trim())
        .map(line => line.replace(/^\d+\.\s*/, '').trim()) || [];

      return suggestions;
    } catch (error) {
      console.error('Error generating prompt suggestions:', error);
      return [];
    }
  };

  const handleTransferToChat = async () => {
    setIsTransferring(true);
    try {
      const analysisContent = `
# Pharmaceutical Analysis Results

${results.paperSummary ? `## Literature Summary\n${results.paperSummary}\n` : ''}

## Drug Development Insights
${results.explanation}

## Gene Clusters and Drug Targets
${results.clusters.map((cluster, index) => `
Cluster ${index + 1}:
${cluster.join(', ')}`).join('\n')}

## Therapeutic Potential
${results.enrichmentResults.map(result => `
- ${result.source}
  - Significance: p-value ${result.pValue.toExponential(2)}
  - Score: ${result.enrichmentScore.toFixed(2)}
  - Targets: ${result.genes.join(', ')}`).join('\n')}`;

      const prompts = await generatePromptSuggestions(analysisContent);

      // Create a new chat for the analysis
      const newChat = createNewChat('Pharmaceutical Analysis');
      
      // Add the analysis content
      newChat.messages = [
        {
          id: uuidv4(),
          role: 'assistant',
          content: analysisContent,
          timestamp: new Date()
        }
      ];

      // Add suggested questions if available
      if (prompts.length > 0) {
        newChat.messages.push({
          id: uuidv4(),
          role: 'assistant',
          content: `Based on the analysis, here are some suggested questions to explore:\n\n${prompts.map((prompt, index) => `[Q${index + 1}] ${prompt}`).join('\n\n')}`,
          timestamp: new Date()
        });
      }

      saveChat(newChat);

      if (onTransferToChat) {
        onTransferToChat();
      }
    } catch (error) {
      console.error('Error transferring to chat:', error);
    } finally {
      setIsTransferring(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex justify-end">
        <button
          onClick={handleTransferToChat}
          disabled={isTransferring}
          className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Share className="h-4 w-4" />
          {isTransferring ? 'Transferring...' : 'Continue in Chat'}
        </button>
      </div>

      {results.tableData && (
        <section className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-100 dark:border-gray-700">
          <DataTable
            headers={results.tableData.headers}
            rows={results.tableData.rows}
            caption={results.tableData.caption}
          />
        </section>
      )}

      <section className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-100 dark:border-gray-700">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-gray-100">
          <BookOpen className="h-5 w-5 text-purple-600 dark:text-purple-400" />
          Literature Summary
        </h3>
        <div className="prose dark:prose-invert max-w-none">
          {results.paperSummary ? (
            <div className="text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-line">
              {results.paperSummary}
            </div>
          ) : (
            <p className="text-gray-500 dark:text-gray-400 italic">
              No literature summary available for this analysis.
            </p>
          )}
        </div>
      </section>

      <section className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-100 dark:border-gray-700">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-gray-100">
          <Brain className="h-5 w-5 text-purple-600 dark:text-purple-400" />
          Analysis Insights
        </h3>
        <div className="prose dark:prose-invert max-w-none">
          {results.explanation}
        </div>
      </section>

      <section className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-100 dark:border-gray-700">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-gray-100">
          <Network className="h-5 w-5 text-purple-600 dark:text-purple-400" />
          Gene Clusters
        </h3>
        <ul className="grid gap-4 md:grid-cols-2">
          {results.clusters.map((cluster, index) => (
            <li
              key={index}
              className="bg-gray-50 dark:bg-gray-700/50 p-4 rounded-lg"
            >
              <span className="font-medium text-gray-900 dark:text-gray-100 mb-3 block">
                Cluster {index + 1}
              </span>
              <ul className="flex flex-wrap gap-2">
                {cluster.map((gene, geneIndex) => (
                  <li
                    key={geneIndex}
                    className="px-3 py-1.5 bg-purple-100 dark:bg-purple-900/50 text-purple-800 dark:text-purple-200 rounded-full text-sm font-medium"
                  >
                    {gene}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}