import streamlit as st
import pandas as pd
from supabase import create_client, Client
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

# Judul Aplikasi
st.title("🚂 Web Laporan Pengoperasian KAI")
st.subheader("🔍 Rekapitulasi Data & Download PDF 4 Halaman")

# 2. Ambil data karyawan untuk dropdown
try:
    karyawan_res = supabase.table("karyawan").select("nipp, nama").execute()
    list_karyawan = karyawan_res.data
except Exception as e:
    st.error(f"Gagal mengambil data karyawan: {e}")
    list_karyawan = []

if list_karyawan:
    dict_karyawan = {k['nama']: k['nipp'] for k in list_karyawan}
    
    col1, col2, col3 = st.columns(3)
    with col1:
        nama_cari = st.selectbox("Nama Karyawan", list(dict_karyawan.keys()))
    with col2:
        bln_cari = st.selectbox("Bulan", [f"{i:02d}" for i in range(1, 13)], index=datetime.datetime.now().month - 1)
    with col3:
        thn_cari = st.text_input("Tahun", value=str(datetime.datetime.now().year))
        
    nipp_cari = dict_karyawan[nama_cari]
    filter_bln = f"{thn_cari}-{bln_cari}"
    
    # Mendapatkan hari terakhir pada bulan tersebut
    try:
        last_day = calendar.monthrange(int(thn_cari), int(bln_cari))[1]
    except:
        last_day = 31

    # 3. Query Data Utama dari tabel 'laporan'
    try:
        res_harian = supabase.table("laporan")\
            .select("*")\
            .eq("nipp", nipp_cari)\
            .gte("tanggal", f"{filter_bln}-01")\
            .lte("tanggal", f"{filter_bln}-{last_day}")\
            .order("tanggal")\
            .execute()
            
        data_harian = res_harian.data if res_harian else []
    except Exception as e:
        st.error(f"Error query database: {e}")
        data_harian = []

    if data_harian:
        df = pd.DataFrame(data_harian)
        
        # Pengaman jika kolom kosong agar tidak memicu KeyError
        kolom_wajib = ["tanggal", "jenis_dinasan", "detail_kegiatan", "serah_terima"]
        for kol in kolom_wajib:
            if kol not in df.columns:
                df[kol] = ""
                
        # Menampilkan tabel di halaman web Streamlit
        st.dataframe(df[kolom_wajib], use_container_width=True)
        
        # 4. Tombol Cetak PDF (Gunakan key unik agar tidak terkena DuplicateElementId)
        if st.button("🖨️ Urutkan & Cetak PDF Resmi", key="btn_cetak_pdf_utama"):
            try:
                abs_data = supabase.table("daftar_hadir")\
                    .select("foto_hadir_url")\
                    .eq("nipp", nipp_cari)\
                    .eq("bulan_tahun", filter_bln)\
                    .execute().data
            except Exception as e:
                abs_data = []
                
            # Pembuatan struktur PDF 
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(100, 8, "REKAPITULASI LAPORAN REAL-TIME", ln=True)
            pdf.set_font("Arial", "", 11)
            pdf.cell(100, 8, f"BULAN: {bln_cari} / {thn_cari}", ln=True)
            pdf.cell(100, 8, f"NAMA: {nama_cari} ({nipp_cari})", ln=True)
            pdf.ln(5)
            
            # Header Tabel PDF
            pdf.set_font("Arial", "B", 10)
            pdf.cell(30, 8, "Hari / Tanggal", border=1)
            pdf.cell(45, 8, "Kegiatan", border=1)
            pdf.cell(55, 8, "Serah Terima Dinasan", border=1)
            pdf.cell(60, 8, "Dokumentasi Kegiatan", border=1, ln=True)
            
            # Isi Baris Tabel PDF
            pdf.set_font("Arial", "", 9)
            for _, row in df.iterrows():
                pdf.cell(30, 10, str(row["tanggal"]), border=1)
                pdf.cell(45, 10, str(row["jenis_dinasan"])[:20], border=1)
                pdf.cell(55, 10, str(row["serah_terima"])[:25], border=1)
                pdf.cell(60, 10, str(row["detail_kegiatan"])[:30], border=1, ln=True)
                
            pdf_output = pdf.output(dest='S').encode('latin-1')
            
            st.download_button(
                label="📥 Download Dokumen PDF Hasil Cetak",
                data=pdf_output,
                file_name=f"Laporan_{nama_cari}_{filter_bln}.pdf",
                mime="application/pdf",
                key="btn_download_proses"
            )
    else:
        st.info("Belum ada entri data laporan untuk bulan ini.")
else:
    st.warning("Data karyawan tidak ditemukan di database.")
