import React from 'react';
import { X } from 'lucide-react';
import { GeneImageViewer } from './GeneImageViewer';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  ensemblId?: string;
  geneName?: string;
}

export function Modal({ isOpen, onClose, ensemblId, geneName }: ModalProps) {
  if (!isOpen || !ensemblId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="relative w-[90vw] max-w-3xl bg-white dark:bg-gray-800 rounded-lg shadow-xl">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <X className="h-5 w-5 text-gray-500 dark:text-gray-400" />
        </button>
        <GeneImageViewer ensemblId={ensemblId} geneName={geneName || ensemblId} />
      </div>
    </div>
  );
}