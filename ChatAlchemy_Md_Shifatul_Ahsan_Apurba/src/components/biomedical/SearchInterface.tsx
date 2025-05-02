import React, { useState } from 'react';
import { Search } from 'lucide-react';

interface SearchInterfaceProps {
  onSearch: (query: string) => void;
}

export function SearchInterface({ onSearch }: SearchInterfaceProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6">
      <h2 className="text-2xl font-semibold mb-4 flex items-center gap-2">
        <Search className="h-6 w-6 text-purple-600 dark:text-purple-400" />
        Search Diseases or Genes
      </h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <div className="relative">
            <input
              type="text"
              id="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., Alzheimer's disease, breast cancer"
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent
                dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400
                transition-colors"
            />
            <button
              type="submit"
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
            >
              <Search className="h-4 w-4" />
            </button>
          </div>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            Search for diseases/genes to analyze their gene associations and potential treatments. 
          </p>
        </div>
      </form>
    </div>
  );
}