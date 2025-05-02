import React, { useState } from 'react';
import { DiseaseModal } from './DiseaseModal';
import { Modal } from './Modal';
import { Download } from 'lucide-react';
import { saveAs } from 'file-saver';
import * as XLSX from 'xlsx';

function capitalizeGene(str: string): string {
  return str.toUpperCase();
}

function capitalizeWords(str: string): string {
  return str.split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ');
}

interface DataTableProps {
  headers: string[];
  rows: any[][];
  caption?: string;
  darkMode?: boolean;
}

export function DataTable({ headers, rows, caption, darkMode = false }: DataTableProps) {
  const [diseaseModalData, setDiseaseModalData] = React.useState<{ efoId: string } | null>(null);
  const [geneModalData, setGeneModalData] = React.useState<{ ensemblId: string; geneName: string } | null>(null);
  const [showAllRows, setShowAllRows] = useState(false);
  const initialRowCount = 10;

  const handleDiseaseClick = (efoId: string) => {
    setDiseaseModalData({ efoId });
  };

  const handleGeneClick = (ensemblId: string, geneName: string) => {
    setGeneModalData({ ensemblId, geneName });
  };

  const handleExportExcel = () => {
    const worksheet = XLSX.utils.aoa_to_sheet([headers, ...rows]);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Gene Analysis');
    
    // Generate buffer
    const excelBuffer = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
    const data = new Blob([excelBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    
    // Save file
    saveAs(data, 'gene-analysis.xlsx');
  };

  const displayedRows = showAllRows ? rows : rows.slice(0, initialRowCount);

  const processCell = (cell: any, cellIndex: number) => {
    if (typeof cell !== 'string') return cell;

    // Process gene symbols (first column)
    if (cellIndex === 0) {
      return {
        __html: `<span class="cursor-pointer hover:text-blue-700 dark:hover:text-blue-300">${capitalizeGene(cell)}</span>`
      };
    }

    // Process Ensembl IDs (third column)
    if (cellIndex === 2 && cell.includes('<a href="https://ensembl.org')) {
      return { __html: cell };
    }

    // Process disease text with EFO IDs (fifth column)
    if (cellIndex === 4) {
      const processedText = cell.replace(/([^[]+)(\[([A-Z]+_\d+)\])?/g, (match: string, diseaseName: string, _: string, efoId: string) => {
        const capitalizedDisease = capitalizeWords(diseaseName.trim());
        return efoId ? 
          `${capitalizedDisease} <button class="text-purple-600 dark:text-purple-400 hover:underline" data-efo-id="${efoId}">[${efoId}]</button>` :
          capitalizedDisease;
      });
      
      return { __html: processedText };
    }

    return cell;
  };

  const handleCellClick = (e: React.MouseEvent<HTMLTableDataCellElement>, row: any[], cellIndex: number) => {
    // Handle disease EFO ID clicks
    const button = (e.target as HTMLElement).closest('button');
    if (button) {
      const efoId = button.getAttribute('data-efo-id');
      if (efoId) {
        handleDiseaseClick(efoId);
        return;
      }
    }

    // Handle gene symbol clicks (first column)
    if (cellIndex === 0) {
      const ensemblId = row[2].match(/g=([^"]+)/)?.[1];
      if (ensemblId) {
        handleGeneClick(ensemblId, row[0]);
      }
    }
  };

  return (
    <>
      <div className="overflow-x-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {caption}
          </h3>
          <button
            onClick={handleExportExcel}
            className="p-2 text-gray-600 dark:text-gray-300 hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
            title="Export to Excel"
          >
            <Download className="h-5 w-5" />
          </button>
        </div>
        
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              {headers.map((header, index) => (
                <th
                  key={index}
                  className="text-left p-4 font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {displayedRows.map((row, rowIndex) => (
              <tr 
                key={rowIndex}
                className={`hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors`}
              >
                {row.map((cell, cellIndex) => {
                  const processedCell = processCell(cell, cellIndex);
                  
                  return (
                    <td
                      key={cellIndex}
                      onClick={(e) => handleCellClick(e, row, cellIndex)}
                      className={`p-4 ${
                        cellIndex === 0 
                          ? 'text-blue-600 dark:text-blue-400 font-medium' 
                          : 'text-gray-600 dark:text-gray-300'
                      }`}
                      {...(typeof processedCell === 'object' ? 
                        { dangerouslySetInnerHTML: processedCell } : 
                        { children: processedCell }
                      )}
                    />
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>

        {rows.length > initialRowCount && (
          <div className="mt-4 text-center">
            <button
              onClick={() => setShowAllRows(!showAllRows)}
              className="px-4 py-2 text-sm text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300"
            >
              {showAllRows ? 'Show Less' : `Show All (${rows.length} rows)`}
            </button>
          </div>
        )}
      </div>
      
      <DiseaseModal
        isOpen={!!diseaseModalData}
        onClose={() => setDiseaseModalData(null)}
        efoId={diseaseModalData?.efoId || ''}
      />

      <Modal
        isOpen={!!geneModalData}
        onClose={() => setGeneModalData(null)}
        ensemblId={geneModalData?.ensemblId}
        geneName={geneModalData?.geneName}
      />
    </>
  );
}