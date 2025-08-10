"""
PDF Processing Service for extracting tables from different document types.

This module handles the extraction of tables from PDF documents using various
libraries like pdfplumber and camelot-py. It provides specialized processing
for each document type (NPT, Rebut, Defauts, Kosu).
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import pdfplumber
from django.core.files.base import ContentFile
from pdf2image import convert_from_path
import numpy as np

try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False

try:
    from paddleocr import PPStructureV3
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False


class PDFProcessor:
    """Main PDF processor class for extracting tables from different document types."""
    
    def __init__(self, document):
        """Initialize the processor with a Document instance."""
        self.document = document
        self.extracted_data = {}
        self.tables = []
        
    def process(self) -> bool:
        """
        Process the PDF document and extract tables based on document type.
        
        Returns:
            bool: True if processing succeeded, False otherwise.
        """
        try:
            self.document.status = 'PROCESSING'
            self.document.save()
            
            # Get the file path
            file_path = self.document.file.path
            
            # Determine the processing method based on document type
            if self.document.document_type:
                doc_type = self.document.document_type.type_code
                
                if doc_type == 'NPT':
                    self._process_npt(file_path)
                elif doc_type == 'REBUT':
                    self._process_rebut(file_path)
                elif doc_type == 'DEFAUTS':
                    self._process_defauts(file_path)
                elif doc_type == 'KOSU':
                    self._process_kosu(file_path)
                else:
                    # Generic processing for unknown types
                    self._process_generic(file_path)
            else:
                # Generic processing if no type specified
                self._process_generic(file_path)
            
            # Save extracted data
            self.document.extracted_data = self.extracted_data
            self.document.table_count = len(self.tables)
            self.document.status = 'COMPLETED'
            self.document.processed_at = datetime.now()
            
            # Generate export files
            self._generate_excel_export()
            self._generate_json_export()
            
            self.document.save()
            return True
            
        except Exception as e:
            self.document.status = 'FAILED'
            self.document.error_message = str(e)
            self.document.save()
            return False
    
    def _process_npt(self, file_path: str):
        """Process NPT type documents."""
        # Try regular extraction first
        self._extract_tables_with_camelot(file_path)
        
        # If no tables found and it might be image-based, try OCR
        used_ocr = False
        if not self.tables:
            self._extract_tables_with_ocr(file_path)
            used_ocr = True
        
        # Custom processing for NPT documents
        processed_tables = []
        for idx, table in enumerate(self.tables):
            # Convert to DataFrame if not already
            if not isinstance(table, pd.DataFrame):
                df = pd.DataFrame(table)
            else:
                df = table
            
            # Clean and structure the data
            df = self._clean_dataframe(df)
            
            # Add metadata
            table_data = {
                'table_index': idx,
                'type': 'NPT',
                'headers': df.columns.tolist() if not df.empty else [],
                'data': df.to_dict('records'),
                'row_count': len(df),
                'column_count': len(df.columns) if not df.empty else 0
            }
            processed_tables.append(table_data)
        
        self.extracted_data = {
            'document_type': 'NPT',
            'total_tables': len(processed_tables),
            'tables': processed_tables,
            'extraction_method': 'paddleocr' if used_ocr else 'camelot'
        }
    
    def _process_rebut(self, file_path: str):
        """Process Rebut type documents."""
        self._extract_tables_with_pdfplumber(file_path)
        
        # If no tables found, try OCR
        used_ocr = False
        if not self.tables:
            self._extract_tables_with_ocr(file_path)
            used_ocr = True
        
        # Custom processing for Rebut documents
        processed_tables = []
        for idx, table in enumerate(self.tables):
            if not isinstance(table, pd.DataFrame):
                df = pd.DataFrame(table)
            else:
                df = table
            
            df = self._clean_dataframe(df)
            
            table_data = {
                'table_index': idx,
                'type': 'REBUT',
                'headers': df.columns.tolist() if not df.empty else [],
                'data': df.to_dict('records'),
                'row_count': len(df),
                'column_count': len(df.columns) if not df.empty else 0
            }
            processed_tables.append(table_data)
        
        self.extracted_data = {
            'document_type': 'REBUT',
            'total_tables': len(processed_tables),
            'tables': processed_tables,
            'extraction_method': 'paddleocr' if used_ocr else 'pdfplumber'
        }
    
    def _process_defauts(self, file_path: str):
        """Process Defauts type documents."""
        print(f"\n{'='*50}")
        print(f"PROCESSING DEFAUTS DOCUMENT")
        print(f"{'='*50}")
        
        print("1. Trying Camelot extraction...")
        self._extract_tables_with_camelot(file_path)
        print(f"   Camelot found {len(self.tables)} tables")
        
        # If no tables found, try OCR
        used_ocr = False
        if not self.tables:
            print("\n2. No tables found with Camelot, trying OCR...")
            self._extract_tables_with_ocr(file_path)
            used_ocr = True
            print(f"   OCR found {len(self.tables)} tables")
        else:
            print("\n2. Tables found with Camelot, skipping OCR")
        
        print("\n3. Processing extracted tables...")
        # Custom processing for Defauts documents
        processed_tables = []
        for idx, table in enumerate(self.tables):
            print(f"   Processing table {idx + 1}/{len(self.tables)}...")
            if not isinstance(table, pd.DataFrame):
                df = pd.DataFrame(table)
            else:
                df = table
            
            df = self._clean_dataframe(df)
            print(f"   Table {idx + 1}: {len(df)} rows × {len(df.columns)} columns")
            
            table_data = {
                'table_index': idx,
                'type': 'DEFAUTS',
                'headers': df.columns.tolist() if not df.empty else [],
                'data': df.to_dict('records'),
                'row_count': len(df),
                'column_count': len(df.columns) if not df.empty else 0
            }
            processed_tables.append(table_data)
        
        print(f"\n4. Finalizing results...")
        self.extracted_data = {
            'document_type': 'DEFAUTS',
            'total_tables': len(processed_tables),
            'tables': processed_tables,
            'extraction_method': 'paddleocr' if used_ocr else 'camelot'
        }
        print(f"   Extraction method: {self.extracted_data['extraction_method']}")
        print(f"   Total tables: {len(processed_tables)}")
        print(f"{'='*50}")
    
    def _process_kosu(self, file_path: str):
        """Process Kosu type documents."""
        self._extract_tables_with_pdfplumber(file_path)
        
        # If no tables found, try OCR
        used_ocr = False
        if not self.tables:
            self._extract_tables_with_ocr(file_path)
            used_ocr = True
        
        # Custom processing for Kosu documents
        processed_tables = []
        for idx, table in enumerate(self.tables):
            if not isinstance(table, pd.DataFrame):
                df = pd.DataFrame(table)
            else:
                df = table
            
            df = self._clean_dataframe(df)
            
            table_data = {
                'table_index': idx,
                'type': 'KOSU',
                'headers': df.columns.tolist() if not df.empty else [],
                'data': df.to_dict('records'),
                'row_count': len(df),
                'column_count': len(df.columns) if not df.empty else 0
            }
            processed_tables.append(table_data)
        
        self.extracted_data = {
            'document_type': 'KOSU',
            'total_tables': len(processed_tables),
            'tables': processed_tables,
            'extraction_method': 'paddleocr' if used_ocr else 'pdfplumber'
        }
    
    def _process_generic(self, file_path: str):
        """Generic processing for unknown document types."""
        # Try both extraction methods
        self._extract_tables_with_camelot(file_path)
        if not self.tables:
            self._extract_tables_with_pdfplumber(file_path)
        if not self.tables:
            self._extract_tables_with_ocr(file_path)
        
        # Process extracted tables
        processed_tables = []
        for idx, table in enumerate(self.tables):
            if not isinstance(table, pd.DataFrame):
                df = pd.DataFrame(table)
            else:
                df = table
            
            df = self._clean_dataframe(df)
            
            table_data = {
                'table_index': idx,
                'type': 'GENERIC',
                'headers': df.columns.tolist() if not df.empty else [],
                'data': df.to_dict('records'),
                'row_count': len(df),
                'column_count': len(df.columns) if not df.empty else 0
            }
            processed_tables.append(table_data)
        
        self.extracted_data = {
            'document_type': 'GENERIC',
            'total_tables': len(processed_tables),
            'tables': processed_tables,
            'extraction_method': 'mixed'
        }
    
    def _extract_tables_with_ocr(self, file_path: str):
        """Extract tables using OCR (PaddleOCR) for image-based PDFs."""
        if not PADDLEOCR_AVAILABLE:
            print("PaddleOCR not available, skipping OCR extraction")
            return
        
        try:
            print("=" * 60)
            print("STARTING PADDLEOCR EXTRACTION")
            print("=" * 60)
            print(f"Processing file: {file_path}")
            print(f"File exists: {os.path.exists(file_path)}")
            print(f"File size: {os.path.getsize(file_path)} bytes")
            
            print("\n1. Initializing PaddleOCR...")
            from paddleocr import PPStructureV3
            
            print("2. Creating PPStructureV3 instance...")
            ocr_engine = PPStructureV3(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_table_recognition=True
            )
            print("✅ PaddleOCR engine created successfully")
            
            print("\n3. Starting PDF prediction...")
            print("   This may take several minutes for large PDFs...")
            print("   Please be patient - OCR is processing...")
            
            start_time = time.time()
            
            def predict_pdf():
                return ocr_engine.predict(input=file_path)
            
            result = predict_pdf()
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            print(f"✅ PDF prediction completed in {elapsed_time:.2f} seconds")
            
            print(f"\n4. Processing results...")
            print(f"   Number of pages found: {len(result)}")
            
            # Extract tables from OCR results
            all_tables = []
            
            for page_idx, page_result in enumerate(result):
                print(f"\n   Processing page {page_idx + 1}/{len(result)}...")
                print(f"   Page result type: {type(page_result)}")
                
                # Try different ways to extract data from the result
                if hasattr(page_result, 'to_dict'):
                    try:
                        print(f"   Page {page_idx + 1} has to_dict method")
                        page_data = page_result.to_dict()
                        print(f"   Page data keys: {list(page_data.keys()) if isinstance(page_data, dict) else 'Not a dict'}")
                        
                        # Look for table structures in the results
                        if 'res' in page_data:
                            print(f"   Found 'res' key in page data")
                            res_items = page_data['res']
                            print(f"   Number of items in 'res': {len(res_items)}")
                            
                            for item_idx, item in enumerate(res_items):
                                print(f"   Item {item_idx + 1}: type={item.get('type', 'unknown')}")
                                if item.get('type') == 'table':
                                    print(f"   🎯 FOUND TABLE on page {page_idx + 1}!")
                                    # Extract table data
                                    table_html = item.get('res', {}).get('html', '')
                                    if table_html:
                                        print(f"   Table has HTML data")
                                        # Parse HTML table to DataFrame
                                        try:
                                            df = pd.read_html(table_html)[0]
                                            all_tables.append(df)
                                            print(f"   ✅ Extracted table with {len(df)} rows and {len(df.columns)} columns")
                                        except Exception as e:
                                            print(f"   ❌ Failed to parse HTML table: {e}")
                                    
                                    # Alternative: use cell data if available
                                    cells = item.get('res', {}).get('cells', [])
                                    if cells and not table_html:
                                        print(f"   Table has cell data: {len(cells)} cells")
                                        # Reconstruct table from cells
                                        df = self._reconstruct_table_from_cells(cells)
                                        if df is not None:
                                            all_tables.append(df)
                                            print(f"   ✅ Reconstructed table with {len(df)} rows and {len(df.columns)} columns")
                        else:
                            print(f"   No 'res' key found in page data")
                    except Exception as e:
                        print(f"   ❌ Error processing page {page_idx + 1}: {e}")
                
                # Try direct attribute access
                elif hasattr(page_result, 'res'):
                    print(f"   Page {page_idx + 1} has res attribute")
                    try:
                        res_items = page_result.res
                        print(f"   Number of items in res: {len(res_items)}")
                        for item_idx, item in enumerate(res_items):
                            print(f"   Item {item_idx + 1}: type={getattr(item, 'type', 'unknown')}")
                            if hasattr(item, 'type') and item.type == 'table':
                                print(f"   🎯 FOUND TABLE on page {page_idx + 1}!")
                                if hasattr(item, 'res'):
                                    # Try to extract table data
                                    if hasattr(item.res, 'html'):
                                        try:
                                            df = pd.read_html(item.res.html)[0]
                                            all_tables.append(df)
                                            print(f"   ✅ Extracted table with {len(df)} rows")
                                        except Exception as e:
                                            print(f"   ❌ Failed to parse HTML: {e}")
                    except Exception as e:
                        print(f"   ❌ Error accessing res attribute: {e}")
                
                # Debug: print what we actually got
                else:
                    print(f"   Page {page_idx + 1} result type: {type(page_result)}")
                    if hasattr(page_result, '__dict__'):
                        attrs = list(page_result.__dict__.keys())
                        print(f"   Available attributes: {attrs[:5]}{'...' if len(attrs) > 5 else ''}")
                    else:
                        print(f"   No __dict__ attribute available")
            
            self.tables = all_tables
            print(f"\n" + "=" * 60)
            print(f"OCR EXTRACTION COMPLETED")
            print(f"Total tables found: {len(all_tables)}")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ OCR extraction failed: {e}")
            import traceback
            traceback.print_exc()
            self.tables = []
    
    def _reconstruct_table_from_cells(self, cells):
        """Reconstruct a table DataFrame from OCR cell data."""
        if not cells:
            return None
        
        try:
            # Find max row and column indices
            max_row = max(cell.get('row_idx', 0) for cell in cells)
            max_col = max(cell.get('col_idx', 0) for cell in cells)
            
            # Create empty table
            table = [['' for _ in range(max_col + 1)] for _ in range(max_row + 1)]
            
            # Fill table with cell data
            for cell in cells:
                row_idx = cell.get('row_idx', 0)
                col_idx = cell.get('col_idx', 0)
                text = cell.get('text', '')
                table[row_idx][col_idx] = text
            
            # Convert to DataFrame
            df = pd.DataFrame(table)
            
            # Try to use first row as headers
            if len(df) > 1:
                potential_headers = df.iloc[0].tolist()
                if all(isinstance(h, str) and h for h in potential_headers):
                    df.columns = potential_headers
                    df = df[1:].reset_index(drop=True)
            
            return df
            
        except Exception as e:
            print(f"Failed to reconstruct table from cells: {e}")
            return None
    
    def _extract_tables_with_camelot(self, file_path: str):
        """Extract tables using Camelot library."""
        if not CAMELOT_AVAILABLE:
            return self._extract_tables_with_pdfplumber(file_path)
        
        try:
            # Try lattice method first (for tables with visible borders)
            tables = camelot.read_pdf(file_path, pages='all', flavor='lattice')
            
            # If no tables found, try stream method (for borderless tables)
            if len(tables) == 0:
                tables = camelot.read_pdf(file_path, pages='all', flavor='stream')
            
            # Convert to DataFrames
            self.tables = [table.df for table in tables]
            
        except Exception as e:
            print(f"Camelot extraction failed: {e}")
            # Fallback to pdfplumber
            self._extract_tables_with_pdfplumber(file_path)
    
    def _extract_tables_with_pdfplumber(self, file_path: str):
        """Extract tables using pdfplumber library."""
        try:
            with pdfplumber.open(file_path) as pdf:
                all_tables = []
                
                for page_num, page in enumerate(pdf.pages):
                    # Extract tables from the page
                    tables = page.extract_tables()
                    
                    for table in tables:
                        if table and len(table) > 0:
                            # Convert to DataFrame
                            df = pd.DataFrame(table)
                            
                            # Try to use first row as headers if it looks like headers
                            if len(df) > 1:
                                potential_headers = df.iloc[0].tolist()
                                if all(isinstance(h, str) and h for h in potential_headers):
                                    df.columns = potential_headers
                                    df = df[1:].reset_index(drop=True)
                            
                            all_tables.append(df)
                
                self.tables = all_tables
                
        except Exception as e:
            print(f"PDFPlumber extraction failed: {e}")
            self.tables = []
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize a DataFrame."""
        # Remove empty rows and columns
        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')
        
        # Convert None values to empty strings
        df = df.fillna('')
        
        # Strip whitespace from string columns
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
        
        # Reset index
        df = df.reset_index(drop=True)
        
        return df
    
    def _generate_excel_export(self):
        """Generate Excel file from extracted data."""
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
                excel_path = tmp_file.name
            
            # Create Excel writer
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # Write summary sheet
                summary_data = {
                    'Property': ['Document Type', 'Total Tables', 'Extraction Method', 'Processed At'],
                    'Value': [
                        self.extracted_data.get('document_type', 'Unknown'),
                        self.extracted_data.get('total_tables', 0),
                        self.extracted_data.get('extraction_method', 'Unknown'),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Write each table to a separate sheet
                tables = self.extracted_data.get('tables', [])
                for idx, table_data in enumerate(tables):
                    sheet_name = f"Table_{idx + 1}"
                    
                    # Convert table data to DataFrame
                    if table_data.get('data'):
                        df = pd.DataFrame(table_data['data'])
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Read the file and save to model
            with open(excel_path, 'rb') as f:
                excel_content = f.read()
            
            # Save to model
            excel_filename = f"{self.document.original_filename.rsplit('.', 1)[0]}_extracted.xlsx"
            self.document.excel_file.save(excel_filename, ContentFile(excel_content))
            
            # Clean up temp file
            os.unlink(excel_path)
            
        except Exception as e:
            print(f"Excel generation failed: {e}")
    
    def _generate_json_export(self):
        """Generate JSON file from extracted data."""
        try:
            # Convert extracted data to JSON
            json_content = json.dumps(self.extracted_data, indent=2, ensure_ascii=False)
            
            # Save to model
            json_filename = f"{self.document.original_filename.rsplit('.', 1)[0]}_extracted.json"
            self.document.json_file.save(json_filename, ContentFile(json_content.encode('utf-8')))
            
        except Exception as e:
            print(f"JSON generation failed: {e}")


def process_document(document) -> bool:
    """
    Process a document and extract tables.
    
    Args:
        document: Document model instance
        
    Returns:
        bool: True if processing succeeded, False otherwise
    """
    processor = PDFProcessor(document)
    return processor.process() 