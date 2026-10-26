import React, { useState, useRef } from 'react';
import {
  Upload,
  FileText,
  Sparkles,
  Loader2,
  AlertCircle,
  CheckCircle2,
  X,
  Layers,
  ArrowRightLeft,
} from 'lucide-react';
import {
  api,
  SAMPLE_CONTRACT,
  SAMPLE_VENDOR_CONTRACT,
  SAMPLE_BUYER_CONTRACT,
} from '../services/api';

const MAX_FILE_SIZE_MB = 25;
const ALLOWED_EXTENSIONS = ['pdf', 'docx', 'doc', 'txt', 'md'];

export default function FileUpload({ onUploadSuccess, onCompareReady }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentFile, setCurrentFile] = useState(null);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const fileInputRef = useRef(null);
  const progressTimerRef = useRef(null);

  const startSimulatedProgress = () => {
    setProgress(15);
    progressTimerRef.current = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) {
          clearInterval(progressTimerRef.current);
          return 90;
        }
        return prev + 15;
      });
    }, 200);
  };

  const finishProgress = () => {
    if (progressTimerRef.current) clearInterval(progressTimerRef.current);
    setProgress(100);
    setTimeout(() => {
      setProgress(0);
      setUploading(false);
    }, 400);
  };

  const handleFile = async (file) => {
    if (!file) return;
    setError(null);
    setSuccessMsg(null);

    // Validate extension
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setError(
        `Unsupported file type ".${ext}". Please upload a PDF, DOCX, or TXT contract.`
      );
      return;
    }

    // Validate size
    if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      setError(
        `File size (${(file.size / (1024 * 1024)).toFixed(1)} MB) exceeds the maximum limit of ${MAX_FILE_SIZE_MB}MB.`
      );
      return;
    }

    setCurrentFile(file.name);
    setUploading(true);
    startSimulatedProgress();

    try {
      const result = await api.uploadContract(file);
      finishProgress();
      setSuccessMsg(
        `Successfully indexed "${file.name}" (${result.total_chunks} FAISS vectors generated).`
      );
      if (onUploadSuccess) onUploadSuccess(result.contract_id);
    } catch (err) {
      if (progressTimerRef.current) clearInterval(progressTimerRef.current);
      setProgress(0);
      setUploading(false);
      setError(err.message || 'Failed to upload and parse contract.');
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleLoadSample = async () => {
    setError(null);
    setSuccessMsg(null);
    setCurrentFile('Enterprise_Cloud_MSA_v2.txt');
    setUploading(true);
    startSimulatedProgress();

    try {
      const result = await api.uploadTextContract(
        'Enterprise_Cloud_MSA_v2.txt',
        SAMPLE_CONTRACT
      );
      finishProgress();
      setSuccessMsg(`Sample Enterprise MSA loaded with ${result.total_chunks} vector chunks.`);
      if (onUploadSuccess) onUploadSuccess(result.contract_id);
    } catch (err) {
      if (progressTimerRef.current) clearInterval(progressTimerRef.current);
      setProgress(0);
      setUploading(false);
      setError(err.message || 'Failed to load sample contract.');
    }
  };

  const handleLoadDemoPair = async () => {
    setError(null);
    setSuccessMsg(null);
    setCurrentFile('Vendor & Buyer Demo MSAs');
    setUploading(true);
    startSimulatedProgress();

    try {
      const [resA, resB] = await Promise.all([
        api.uploadTextContract('Vendor_SaaS_Agreement.txt', SAMPLE_VENDOR_CONTRACT),
        api.uploadTextContract('Buyer_Enterprise_Agreement.txt', SAMPLE_BUYER_CONTRACT),
      ]);
      finishProgress();
      setSuccessMsg(
        'Loaded 2 demo contracts for side-by-side comparison and cross-clause auditing.'
      );
      if (onCompareReady) {
        onCompareReady(resA.contract_id, resB.contract_id);
      } else if (onUploadSuccess) {
        onUploadSuccess(resA.contract_id);
      }
    } catch (err) {
      if (progressTimerRef.current) clearInterval(progressTimerRef.current);
      setProgress(0);
      setUploading(false);
      setError(err.message || 'Failed to load demo contract pair.');
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-slate-800 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center space-x-2">
            <FileText className="w-5 h-5 text-emerald-400" />
            <span>Ingest Commercial Agreement</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            PDF, DOCX, or TXT • Chunked & indexed in in-memory FAISS
          </p>
        </div>

        {/* Explicitly Labeled Demo Mode Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleLoadSample}
            disabled={uploading}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 hover:border-emerald-500/50 text-xs font-semibold shadow-sm transition disabled:opacity-50"
            title="Load sample enterprise MSA for single-contract risk audit"
          >
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            <span>Demo: Enterprise MSA</span>
          </button>

          <button
            onClick={handleLoadDemoPair}
            disabled={uploading}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/20 transition disabled:opacity-50"
            title="Load 2 contrasting contracts for side-by-side comparison"
          >
            <ArrowRightLeft className="w-3.5 h-3.5 text-emerald-200" />
            <span>Demo: Comparison Pair</span>
          </button>
        </div>
      </div>

      {/* Drag & Drop Area */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current && fileInputRef.current.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
          isDragging
            ? 'border-emerald-400 bg-emerald-500/5 scale-[1.01]'
            : 'border-slate-700 hover:border-slate-500 bg-slate-900/40'
        } ${uploading ? 'opacity-80 pointer-events-none' : ''}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.doc,.txt,.md"
          className="hidden"
          disabled={uploading}
          onChange={(e) => {
            if (e.target.files.length > 0) handleFile(e.target.files[0]);
          }}
        />

        <div className="flex flex-col items-center justify-center space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            {uploading ? (
              <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
            ) : (
              <Upload className="w-6 h-6" />
            )}
          </div>

          <div>
            <p className="text-sm font-medium text-slate-200">
              {uploading
                ? `Ingesting & indexing "${currentFile}"...`
                : 'Click to upload contract or drag & drop file here'}
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Supports .pdf, .docx, and .txt files up to 25MB
            </p>
          </div>

          {/* Upload Progress Bar */}
          {uploading && (
            <div className="w-full max-w-xs space-y-1 pt-2">
              <div className="flex justify-between text-[11px] text-slate-400 font-mono">
                <span>Vector Indexing</span>
                <span>{progress}%</span>
              </div>
              <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Success Notification */}
      {successMsg && (
        <div className="mt-3 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between text-xs text-emerald-300 animate-fadeIn">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button
            onClick={() => setSuccessMsg(null)}
            className="text-slate-400 hover:text-white p-0.5"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="mt-3 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-between text-xs text-rose-400 animate-fadeIn">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-slate-400 hover:text-white p-0.5"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
