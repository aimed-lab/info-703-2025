import React from 'react';
import { Loader2 } from 'lucide-react';

export function LoadingState() {
  return (
    <div className="flex items-center justify-center p-8 bg-white dark:bg-gray-800 rounded-lg">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="w-8 h-8 text-purple-600 dark:text-purple-400 animate-spin" />
        <p className="text-gray-600 dark:text-gray-300">
          Processing biomedical data...
        </p>
      </div>
    </div>
  );
}