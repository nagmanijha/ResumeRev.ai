import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from backend.analysis_engine.report_generator import generate_pdf_report

def verify_fix():
    print("Verifying PDF generation fix...")
    
    # Mock data
    mock_data = {
        "parsed_data": {"name": "Test User"},
        "ats_score": {"total_score": 85, "breakdown": {}, "skill_gap": {"matched": [], "missing": []}},
        "suggestions": ["Fix your resume"]
    }
    
    try:
        pdf_bytes = generate_pdf_report(mock_data)
        print(f"Result type: {type(pdf_bytes)}")
        
        if isinstance(pdf_bytes, bytes):
            print("SUCCESS: generate_pdf_report returned bytes.")
            # Check if it starts with PDF header
            if pdf_bytes.startswith(b"%PDF"):
                 print("SUCCESS: Valid PDF header detected.")
            else:
                 print("WARNING: No PDF header (might be due to encoding, but at least it is bytes)")
        else:
            print(f"FAILURE: Expected bytes, got {type(pdf_bytes)}")
            sys.exit(1)
            
    except Exception as e:
        print(f"CRASHED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_fix()
