import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import warnings

st.set_page_config(page_title="LDC Document Auditor Ultra", page_icon="🚢", layout="wide")
warnings.filterwarnings("ignore", category=FutureWarning)

# --- 1. CONFIGURATION ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("API Key belum disetting di Secrets!")

def get_dynamic_model():
    """Mencari model terbaru yang tersedia secara otomatis"""
    try:
        # Mengambil daftar model yang didukung akunmu
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # Prioritas: Cari yang ada kata 'pro', jika tidak ada pakai apa saja yang tersedia
                if 'pro' in m.name:
                    return m.name
        # Jika tidak ada 'pro', ambil model pertama yang tersedia
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return models[0] if models else "models/gemini-1.5-flash"
    except Exception as e:
        return "models/gemini-1.5-flash"

def extract_pdf_hybrid(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    image_parts = []
    extracted_text = ""
    for page in doc:
        extracted_text += page.get_text("text") + "\n"
        pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0)) 
        img_data = pix.tobytes("jpg")
        image_parts.append({"mime_type": "image/jpeg", "data": img_data})
    return image_parts, extracted_text

# --- 2. UI ---
st.title("🚢 LDC Auditor - Auto-Model Sync")

with st.sidebar:
    st.header("Instruksi Khusus")
    notes = st.text_area("Tambahkan catatan tambahan:", height=150)
    st.info("Sistem akan mendeteksi model AI terbaru dari Google secara otomatis.")

uploaded_files = st.file_uploader("Upload PDF Dokumen Ekspor", type=['pdf'], accept_multiple_files=True)

if st.button("JALANKAN AUDIT SEKARANG", type="primary"):
    if not uploaded_files:
        st.error("Upload file dulu ya!")
    else:
        with st.status("Sedang sinkronisasi dengan server Google...", expanded=True) as status:
            try:
                # MENCARI MODEL SECARA OTOMATIS
                target_model = get_dynamic_model()
                st.write(f"✅ Terkoneksi ke: **{target_model}**")
                
                model = genai.GenerativeModel(target_model)
                
                prompt_parts = [
                    "Kamu adalah Senior Auditor Ekspor paling teliti. Tugasmu adalah Zero Tolerance Error!\n"
                    "PERHATIAN: Gunakan TEKS ASLI sebagai acuan utama jika gambarnya kurang jelas.\n"
                    "1. IDENTIFIKASI MASTER: File 'BL' atau 'Bill of Lading' adalah kebenaran mutlak.\n"
                    "2. ALAMAT SHIPPER PATEN (Wajib Sama Persis):\n"
                    "   PT. LDC TRADING INDONESIA\n"
                    "   GEDUNG WISMA 46 - KOTA BNI LANTAI 15 SUITE 15.01, 15.10-12\n"
                    "   JL JEND. SUDIRMAN KAV 1, KARET TENGSIN, TANAH ABANG,\n"
                    "   KOTA ADM. JAKARTA PUSAT, DKI JAKARTA, 10220, INDONESIA\n"
                    "3. DATA WAJIB AUDIT:\n"
                    "   - SHIPPER, CONSIGNEE, GROSS & NET WEIGHT, MARKING, VESSEL, VOYAGE, LOADING, DISCHARGE, CONTAINER & SEAL NUMBER.\n"
                    "4. INSTRUKSI KHUSUS:\n"
                    "   - Cek angka koma dan titik pada Weight. Beda 0.01 pun ERROR.\n"
                    "   - Pastikan nomor Container dan Seal tidak kurang atau lebih 1 digit.\n"
                    "   - Bandingkan semua dokumen pendukung terhadap MASTER BL.\n\n"
                    "FORMAT TABEL:\n"
                    "| Field | Data Master (BL) | Data Dokumen Ini | Status | Solusi |\n"
                    "| :--- | :--- | :--- | :--- | :--- |\n"
                    f"CATATAN TAMBAHAN: {notes}"
                ]

                for uploaded_file in uploaded_files:
                    img_parts, raw_text = extract_pdf_hybrid(uploaded_file)
                    prompt_parts.append(f"\n--- DATA DARI FILE: {uploaded_file.name} ---\n")
                    prompt_parts.append(f"TEKS DIGITAL:\n{raw_text}")
                    prompt_parts.extend(img_parts)

                response = model.generate_content(prompt_parts)
                
                status.update(label="Audit Selesai!", state="complete", expanded=False)
                st.markdown("### 📋 Laporan Hasil Audit")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"Terjadi kesalahan teknis: {str(e)}")
