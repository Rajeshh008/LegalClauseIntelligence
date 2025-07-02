import streamlit as st
import pandas as pd
import os
from io import BytesIO
import tempfile
from processing.extract_text import extract_text_from_file
from processing.detect_clauses import detect_clauses
from processing.summarize_and_flag import analyze_clauses_with_gemini
import traceback

def main():
    st.set_page_config(
        page_title="Legal Contract Analyzer",
        page_icon="📋",
        layout="wide"
    )
    
    st.title("📋 Legal Contract Analyzer")
    st.markdown("*Analyze legal contracts with AI-powered clause extraction and risk assessment*")
    
    # Sidebar for instructions
    with st.sidebar:
        st.header("📖 How to Use")
        st.markdown("""
        1. **Upload** a PDF or DOCX contract file
        2. **Or paste** raw contract text
        3. **Click** 'Analyze Contract' to process
        4. **Review** extracted clauses with summaries
        5. **Check** risk flags for potential concerns
        6. **Export** results as CSV if needed
        """)
        
        st.header("⚠️ Disclaimer")
        st.warning("This tool is for informational purposes only and does not constitute legal advice. Always consult with a qualified attorney for legal matters.")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📄 Contract Input")
        
        # File upload option
        uploaded_file = st.file_uploader(
            "Upload Contract File",
            type=['pdf', 'docx'],
            help="Upload a PDF or Word document containing your legal contract"
        )
        
        # Text input option
        st.markdown("**OR**")
        contract_text = st.text_area(
            "Paste Contract Text",
            height=200,
            placeholder="Paste your contract text here...",
            help="Copy and paste the text content of your contract"
        )
        
        # Analysis button
        analyze_button = st.button("🔍 Analyze Contract", type="primary")
    
    with col2:
        st.header("📊 Analysis Status")
        status_container = st.container()
    
    # Process contract when button is clicked
    if analyze_button:
        if not uploaded_file and not contract_text.strip():
            st.error("Please upload a file or paste contract text to analyze.")
            return
        
        try:
            with status_container:
                with st.spinner("Processing contract..."):
                    # Extract text from file or use pasted text
                    if uploaded_file:
                        with st.status("Extracting text from file...") as status:
                            # Save uploaded file temporarily
                            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                                tmp_file.write(uploaded_file.getvalue())
                                tmp_file_path = tmp_file.name
                            
                            try:
                                extracted_text = extract_text_from_file(tmp_file_path)
                                status.update(label="Text extracted successfully!", state="complete")
                            finally:
                                # Clean up temporary file
                                os.unlink(tmp_file_path)
                    else:
                        extracted_text = contract_text.strip()
                        st.success("Using pasted text for analysis")
                    
                    if not extracted_text.strip():
                        st.error("No text could be extracted from the file. Please check the file format.")
                        return
                    
                    # Detect clauses
                    with st.status("Detecting contract clauses...") as status:
                        clauses = detect_clauses(extracted_text)
                        status.update(label=f"Found {len(clauses)} clauses", state="complete")
                    
                    if not clauses:
                        st.warning("No clauses could be detected in the contract text.")
                        return
                    
                    # Analyze clauses with Gemini AI
                    with st.status("Analyzing clauses with AI...") as status:
                        analyzed_clauses = analyze_clauses_with_gemini(clauses)
                        status.update(label="AI analysis complete!", state="complete")
            
            # Display results
            st.header("📋 Analysis Results")
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Clauses", len(analyzed_clauses))
            with col2:
                risky_clauses = sum(1 for clause in analyzed_clauses if clause.get('risk_flag', False))
                st.metric("Risky Clauses", risky_clauses)
            with col3:
                clause_types = set(clause.get('clause_type', 'Unknown') for clause in analyzed_clauses)
                st.metric("Clause Types", len(clause_types))
            with col4:
                safe_clauses = len(analyzed_clauses) - risky_clauses
                st.metric("Safe Clauses", safe_clauses)
            
            # Display each clause
            for i, clause_data in enumerate(analyzed_clauses, 1):
                with st.expander(f"Clause {i}: {clause_data.get('clause_type', 'Unknown')} {'⚠️' if clause_data.get('risk_flag', False) else '✅'}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.subheader("Original Text")
                        st.text_area(
                            f"clause_{i}_original",
                            value=clause_data.get('original_text', ''),
                            height=100,
                            disabled=True,
                            label_visibility="collapsed"
                        )
                        
                        st.subheader("Plain English Summary")
                        st.write(clause_data.get('summary', 'No summary available'))
                    
                    with col2:
                        st.subheader("Clause Information")
                        st.write(f"**Type:** {clause_data.get('clause_type', 'Unknown')}")
                        
                        if clause_data.get('risk_flag', False):
                            st.error("⚠️ **Risk Detected**")
                            st.write(f"**Risk Reason:** {clause_data.get('risk_reason', 'No reason provided')}")
                        else:
                            st.success("✅ **No Significant Risk**")
            
            # Export functionality
            st.header("📤 Export Results")
            
            # Prepare data for export
            export_data = []
            for i, clause_data in enumerate(analyzed_clauses, 1):
                export_data.append({
                    'Clause_Number': i,
                    'Clause_Type': clause_data.get('clause_type', 'Unknown'),
                    'Original_Text': clause_data.get('original_text', ''),
                    'Summary': clause_data.get('summary', ''),
                    'Risk_Flag': 'Yes' if clause_data.get('risk_flag', False) else 'No',
                    'Risk_Reason': clause_data.get('risk_reason', '') if clause_data.get('risk_flag', False) else ''
                })
            
            df = pd.DataFrame(export_data)
            
            # Convert DataFrame to CSV
            csv_buffer = BytesIO()
            df.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()
            
            st.download_button(
                label="📥 Download as CSV",
                data=csv_data,
                file_name="contract_analysis.csv",
                mime="text/csv"
            )
            
            # Display table
            st.subheader("Results Table")
            st.dataframe(df, use_container_width=True)
            
        except Exception as e:
            st.error(f"An error occurred during analysis: {str(e)}")
            if st.checkbox("Show detailed error information"):
                st.text(traceback.format_exc())

if __name__ == "__main__":
    main()
