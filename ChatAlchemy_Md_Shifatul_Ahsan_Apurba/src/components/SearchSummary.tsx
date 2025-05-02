import React from 'react';
import { SearchResult } from '../types';
import { Database, Search, Filter, Columns } from 'lucide-react';

interface SearchSummaryProps {
  result: SearchResult;
  darkMode?: boolean;
}

export function SearchSummary({ result, darkMode = false }: SearchSummaryProps) {
  const { searchDetails } = result;

  return (
    <div className={`mt-4 p-4 rounded-lg ${
      darkMode ? 'bg-gray-800 text-gray-300' : 'bg-gray-100 text-gray-700'
    }`}>
      <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
        <Search className="w-4 h-4" />
        Search Analysis
      </h3>
      
      <div className="space-y-4">
        <div>
          <div className="flex items-center gap-2 mb-2 text-sm font-medium">
            <Database className="w-4 h-4" />
            Data Sources ({searchDetails.sources.length})
          </div>
          <div className="text-sm pl-6">
            {searchDetails.sources.length > 0 ? (
              <ul className="list-disc space-y-1">
                {searchDetails.sources.map((source, index) => (
                  <li key={index}>{source}</li>
                ))}
              </ul>
            ) : (
              <p className="italic">No data sources available</p>
            )}
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-2 text-sm font-medium">
            <Columns className="w-4 h-4" />
            Available Fields
          </div>
          <div className="text-sm pl-6">
            {searchDetails.availableColumns.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {searchDetails.availableColumns.map((column, index) => (
                  <span
                    key={index}
                    className={`px-2 py-1 rounded text-xs ${
                      darkMode 
                        ? 'bg-gray-700 text-gray-300' 
                        : 'bg-gray-200 text-gray-700'
                    }`}
                  >
                    {column}
                  </span>
                ))}
              </div>
            ) : (
              <p className="italic">No fields available</p>
            )}
          </div>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-2 text-sm font-medium">
            <Filter className="w-4 h-4" />
            Search Parameters
          </div>
          <div className="text-sm pl-6 space-y-2">
            <div>
              <strong>Terms:</strong>{' '}
              {searchDetails.searchTerms.length > 0 ? (
                <span className="font-mono">{searchDetails.searchTerms.join(', ')}</span>
              ) : (
                <span className="italic">None</span>
              )}
            </div>
            
            <div>
              <strong>Filters:</strong>{' '}
              {searchDetails.conditions.length > 0 ? (
                <span className="font-mono">
                  {searchDetails.conditions.map(c => `${c.field}=${c.value}`).join(', ')}
                </span>
              ) : (
                <span className="italic">None</span>
              )}
            </div>

            <div>
              <strong>Selected Fields:</strong>{' '}
              {searchDetails.requestedColumns.length > 0 ? (
                <span className="font-mono">{searchDetails.requestedColumns.join(', ')}</span>
              ) : (
                <span className="italic">All fields</span>
              )}
            </div>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <p className="text-sm font-medium">
            Found {searchDetails.totalRecords} matching records
          </p>
        </div>
      </div>
    </div>
  );
}