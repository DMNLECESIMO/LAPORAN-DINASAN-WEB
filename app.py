import streamlit as st
import pandas as pd
from supabase import create_client
from fpdf import FPDF
import datetime
import calendar

# 1. Inisialisasi Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# 2. Struktur Menu Navigasi Sidebar (Lengkap)
st.sidebar.title("Navigasi Aplikasi")
menu = st.sidebar.selectbox(
    "Menu Utama", 
    ["Beranda", "Input Data Karyawan", "Input Laporan Harian", "Pencarian & Cetak PDF"]
)

# ==========================================================
# HALAMAN 1: BERANDA
# ==========================================================
if menu == "Beranda":
    st.title("🚂 Sistem Web Laporan Pengoperasian KAI")
    st.write("Selamat datang di sistem manajemen data dinasan.")
    st.info("Pilih menu di sidebar untuk melakukan input data atau mencetak laporan.")

# ==========================================================
# HALAMAN 2: INPUT DATA KARYAWAN
# ==========================================================
elif menu == "Input Data Karyawan":
    st.title("👥 Input Data Karyawan Baru")
    with st.form("form_karyawan", clear_on_submit=True):
        nipp = st.text_input("NIPP Karyawan")
        nama = st.text_input("Nama Lengkap")
        if st.form_submit_button("Simpan Data Karyawan"):
            if nipp and nama:
                supabase.table("karyawan").insert({"nipp": nipp, "nama": nama}).execute()
                st.success(f"Karyawan {nama} berhasil disimpan.")
            else:
                st.warning("Mohon isi semua kolom.")

# ==========================================================
# HALAMAN 3: INPUT LAPORAN HARIAN
# ==========================================================
elif menu == "Input Laporan Harian":
    st.title("📝 Input Laporan Harian")
    karyawan = supabase.table("karyawan").select("nipp, nama").execute().data
    dict_kry = {k['nama']: k['nipp'] for k in karyawan}
    
    with st.form("form_laporan", clear_on_submit=True):
        nama_pilih = st.selectbox("Pilih Karyawan", list(dict_kry.keys()))
        tgl = st.date_input("Tanggal")
        jenis = st.text_input("Jenis Dinasan")
        kegiatan = st.text_area("Detail Kegiatan")
        serah = st.text_input("Serah Terima")
        
        if st.form_submit_button("Simpan Laporan Harian"):
            supabase.table("laporan").insert({
                "nipp": dict_kry[nama_pilih], 
                "tanggal": str(tgl), 
                "jenis_dinasan": jenis,
                "detail_kegiatan": kegiatan,
                "serah_terima": serah
            }).execute()
            st.success("Laporan berhasil tersimpan!")

# ==========================================================
# HALAMAN 4: PENCARIAN & CETAK PDF (STABIL)
# ==========================================================
elif menu == "Pencarian & Cetak PDF":
    st.title("🚂 Web Laporan Pengoperasian KAI")
    st.subheader("🔍 Rekapitulasi Data & Download PDF")

    # Pencarian
    col1, col2 = st.columns(2)
    with col1:
        thn = st.text_input("Tahun", value=str(datetime.datetime.now().year))
    with col2:
        bln = st.selectbox("Bulan", [f"{i:02d}" for i in range(1, 13)])
        
    if st.button("Tampilkan Data"):
        res = supabase.table("laporan").select("*").execute().data
        df = pd.DataFrame(res)
        st.dataframe(df)
        # Simpan ke session_state agar PDF tetap bisa dibuat setelah tombol klik
        st.session_state['df_report'] = df
        st.session_state['ready_pdf'] = True

    # Tombol download diletakkan di luar blok pencarian agar stabil
    if st.session_state.get('ready_pdf'):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, "LAPORAN DINASAN", ln=True, align='C')
        pdf.set_font("Arial", size=10)
        
        for _, row in st.session_state['df_report'].iterrows():
            txt = f"Tanggal: {row.get('tanggal')} | Kegiatan: {row.get('jenis_dinasan')}"
            pdf.cell(200, 8, txt, ln=True)
            
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        
        st.download_button(
            label="📥 Download PDF Sekarang",
            data=pdf_bytes,
            file_name="Laporan_KAI.pdf",
            mime="application/pdf"
        )
