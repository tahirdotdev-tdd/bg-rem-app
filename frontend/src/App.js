import React, { useState, useCallback } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Drag and Drop Component
const ImageDropzone = ({ onImageDrop, isProcessing }) => {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    const imageFile = files.find(file => file.type.startsWith('image/'));
    
    if (imageFile) {
      onImageDrop(imageFile);
    }
  }, [onImageDrop]);

  const handleFileSelect = useCallback((e) => {
    const file = e.target.files[0];
    if (file && file.type.startsWith('image/')) {
      onImageDrop(file);
    }
  }, [onImageDrop]);

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        className={`
          relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
          transition-all duration-300 ease-in-out
          ${isDragOver 
            ? 'border-blue-500 bg-blue-50 scale-105' 
            : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
          }
          ${isProcessing ? 'pointer-events-none opacity-50' : ''}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => document.getElementById('file-input').click()}
      >
        <input
          id="file-input"
          type="file"
          accept="image/*"
          onChange={handleFileSelect}
          className="hidden"
          disabled={isProcessing}
        />
        
        <div className="space-y-4">
          <div className="mx-auto w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          
          <div>
            <p className="text-xl font-semibold text-gray-700 mb-2">
              {isProcessing ? 'Processing...' : 'Drop your image here'}
            </p>
            <p className="text-gray-500">
              {isProcessing ? 'Removing background, please wait...' : 'or click to browse files'}
            </p>
          </div>
          
          <div className="text-sm text-gray-400">
            Supports JPG, PNG, WEBP
          </div>
        </div>
      </div>
    </div>
  );
};

// Image Preview Component
const ImagePreview = ({ originalImage, processedImage, onDownload, onClear, processingTime }) => {
  const [showOriginal, setShowOriginal] = useState(false);
  
  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {/* Toggle Button */}
      <div className="flex justify-center">
        <div className="bg-gray-100 p-1 rounded-lg">
          <button
            onClick={() => setShowOriginal(false)}
            className={`px-4 py-2 rounded-md transition-all ${
              !showOriginal 
                ? 'bg-white shadow-sm text-blue-600 font-medium' 
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Result
          </button>
          <button
            onClick={() => setShowOriginal(true)}
            className={`px-4 py-2 rounded-md transition-all ${
              showOriginal 
                ? 'bg-white shadow-sm text-blue-600 font-medium' 
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Original
          </button>
        </div>
      </div>

      {/* Image Display */}
      <div className="relative bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="aspect-video bg-gray-50 flex items-center justify-center p-4">
          <img
            src={showOriginal ? originalImage : `data:image/png;base64,${processedImage}`}
            alt={showOriginal ? "Original" : "Background Removed"}
            className="max-w-full max-h-full object-contain rounded-lg shadow-md"
          />
        </div>
        
        {/* Image overlay info */}
        <div className="absolute top-4 left-4 bg-black bg-opacity-50 text-white px-3 py-1 rounded-full text-sm">
          {showOriginal ? 'Original' : 'Background Removed'}
        </div>
      </div>

      {/* Stats and Actions */}
      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="text-sm text-gray-500">
          {processingTime && `Processed in ${processingTime.toFixed(2)}s`}
        </div>
        
        <div className="flex gap-3">
          <button
            onClick={onClear}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            New Image
          </button>
          <button
            onClick={onDownload}
            className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all transform hover:scale-105 shadow-lg"
          >
            Download PNG
          </button>
        </div>
      </div>
    </div>
  );
};

// Main App Component
function App() {
  const [originalImage, setOriginalImage] = useState(null);
  const [processedImage, setProcessedImage] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [processingTime, setProcessingTime] = useState(null);

  const convertFileToBase64 = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };

  const handleImageDrop = async (file) => {
    try {
      setError(null);
      setIsProcessing(true);
      setProcessedImage(null);
      
      // Convert file to base64 for preview
      const originalImageData = await convertFileToBase64(file);
      setOriginalImage(originalImageData);
      
      // Prepare for API call
      const base64Data = originalImageData.split(',')[1];
      
      // Call API
      const response = await axios.post(`${API}/remove-background`, {
        image_data: base64Data,
        filename: file.name
      });

      if (response.data.success) {
        setProcessedImage(response.data.processed_image);
        setProcessingTime(response.data.processing_time);
      } else {
        setError(response.data.error || 'Processing failed');
      }
      
    } catch (err) {
      console.error('Error processing image:', err);
      setError(err.response?.data?.detail || 'Failed to process image');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = () => {
    if (!processedImage) return;
    
    const link = document.createElement('a');
    link.href = `data:image/png;base64,${processedImage}`;
    link.download = 'background-removed.png';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleClear = () => {
    setOriginalImage(null);
    setProcessedImage(null);
    setError(null);
    setProcessingTime(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="text-center py-12">
        <h1 className="text-4xl font-bold text-gray-800 mb-4">
          Background Remover
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          Remove backgrounds from your images instantly with AI. 
          Simply drag & drop or click to upload.
        </p>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 pb-12">
        {error && (
          <div className="max-w-2xl mx-auto mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600 text-center">{error}</p>
          </div>
        )}

        {!processedImage ? (
          <ImageDropzone 
            onImageDrop={handleImageDrop} 
            isProcessing={isProcessing}
          />
        ) : (
          <ImagePreview
            originalImage={originalImage}
            processedImage={processedImage}
            onDownload={handleDownload}
            onClear={handleClear}
            processingTime={processingTime}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="text-center py-8 text-gray-500 text-sm">
        <p>Free & Open Source Background Removal Tool</p>
      </footer>
    </div>
  );
}

export default App;