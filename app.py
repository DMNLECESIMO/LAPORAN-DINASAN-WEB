import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import requests
from io import BytesIO

# --- HUBUNGKAN KE SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="Laporan Operasional KAI", layout="wide")
st.title("🚂 Web Laporan Pengoperasian KAI")

menu = ["Input Profil Karyawan", "Input Laporan Harian & Absensi", "Pencarian & Cetak PDF"]
choice = st.sidebar.selectbox("Menu Utama", menu)

def upload_foto(file, folder_name, file_name):
    if file:
        bytes_data = file.getvalue()
        path_on_supa = f"{folder_name}/{file_name}.png"
        supabase.storage.from_("dokumentasi").remove([path_on_supa])
        supabase.storage.from_("dokumentasi").upload(path=path_on_supa, file=bytes_data, file_options={"content-type": "image/png"})
        return supabase.storage.from_("dokumentasi").get_public_url(path_on_supa)
    return None

# --- MENU 1: INPUT PROFIL KARYAWAN ---
if choice == "Input Profil Karyawan":
    st.header("👤 Master Data Karyawan & Smartcard")
    with st.form("form_k"):
        nipp = st.text_input("NIPP")
        nama = st.text_input("Nama Lengkap")
        jabatan = st.text_input("Jabatan", value="KS DINAS / PPKA")
        unit = st.text_input("Unit Kerja / UPT STASIUN")
        daop = st.text_input("DAOP")
        foto_sc = st.file_uploader("Upload / Update Foto Smartcard Kecakapan (PKA)", type=["png", "jpg", "jpeg"])
        if st.form_submit_button("Simpan Data Karyawan"):
            sc_url = upload_foto(foto_sc, "smartcard", f"sc_{nipp}") if foto_sc else None
            data = {"nipp": nipp, "nama": nama, "jabatan": jabatan, "unit_kerja": unit, "daop": daop}
            if sc_url: data["sc_url"] = sc_url
            
            check = supabase.table("karyawan").select("*").eq("nipp", nipp).execute()
            if check.data:
                supabase.table("karyawan").update(data).eq("nipp", nipp).execute()
            else:
                supabase.table("karyawan").insert(data).execute()
            st.success("Data Karyawan Berhasil Disimpan!")

# --- MENU 2: INPUT LAPORAN HARIAN & ABSENSI ---
elif choice == "Input Laporan Harian & Absensi":
    st.header("📝 Input Laporan Real-Time Dinasan")
    k_data = supabase.table("karyawan").select("nipp, nama").execute().data
    if not k_data:
        st.warning("Isi data karyawan terlebih dahulu di Menu 1.")
    else:
        opt_k = {f"{k['nipp']} - {k['nama']}": k['nipp'] for k in k_data}
        pilih_k = st.selectbox("Pilih Karyawan", list(opt_k.keys()))
        nipp_terpilih = opt_k[pilih_k]
        
        st.subheader("1. Upload Absensi Bulanan (Halaman 3)")
        bln_absensi = st.date_input("Pilih Bulan Absensi", datetime.now()).strftime("%Y-%m")
        foto_absen = st.file_uploader("Foto Lembar Daftar Hadir Bulanan", type=["png", "jpg", "jpeg"], key="absen")
        if st.button("Simpan Absensi Bulanan"):
            if foto_absen:
                url_absen = upload_foto(foto_absen, "absensi", f"abs_{nipp_terpilih}_{bln_absensi}")
                supabase.table("daftar_hadir").insert({"nipp": nipp_terpilih, "bulan_tahun": bln_absensi, "foto_hadir_url": url_absen}).execute()
                st.success("Daftar hadir bulanan berhasil tersimpan!")
        
        st.markdown("---")
        st.subheader("2. Input Giat Harian & Dokumentasi (Halaman 4)")
        tgl = st.date_input("Tanggal Dinasan", datetime.now()).strftime("%Y-%m-%d")
        jns = st.selectbox("Jenis Dinasan", ["DINAS KS", "DINAS PPKA PAGI", "DINAS PPKA SIANG", "DINAS PPKA MALAM", "LIBUR", "CUTI", "SAKIT", "SERTIFIKASI", "PEMBINAAN", "DINAS LUAR"])
        keg = st.text_area("Detail Kegiatan / Dinasan")
        serah = st.text_area("Serah Terima Dinasan")
        f1 = st.file_uploader("Foto Dokumentasi Kegiatan 1", type=["png", "jpg", "jpeg"], key="f1")
        f2 = st.file_uploader("Foto Dokumentasi Kegiatan 2", type=["png", "jpg", "jpeg"], key="f2")
        
        if st.button("Simpan Laporan Harian"):
            url_f1 = upload_foto(f1, "harian", f"f1_{nipp_terpilih}_{tgl}") if f1 else jns
            url_f2 = upload_foto(f2, "harian", f"f2_{nipp_terpilih}_{tgl}") if f2 else jns
            
            harian_data = {"nipp": nipp_terpilih, "tanggal": str(tgl), "jenis_dinasan": jns, "detail_kegiatan": keg, "serah_terima": serah, "dok_url": url_f1}
            check_h = supabase.table("laporan").select("*").eq("nipp", nipp_terpilih).eq("tanggal", tgl).execute()
            if check_h.data:
                supabase.table("laporan").update(harian_data).eq("nipp", nipp_terpilih).eq("tanggal", tgl).execute()
            else:
                supabase.table("laporan").insert(harian_data).execute()
            st.success("Laporan harian berhasil disimpan!")

# --- MENU 3: PENCARIAN & CETAK PDF TEMPLATE PERSIS ---
elif choice == "Pencarian & Cetak PDF":
    st.header("🔍 Rekapitulasi Data & Download PDF 4 Halaman")
    k_data = supabase.table("karyawan").select("nipp, nama").execute().data
    if k_data:
        opt_k = {k['nama']: k['nipp'] for k in k_data}
        c1, c2, c3 = st.columns(3)
        with c1: nama_cari = st.selectbox("Nama Karyawan", list(opt_k.keys()))
        with c2: bln_cari = st.selectbox("Bulan", [f"{i:02d}" for i in range(1,13)], index=datetime.now().month-1)
        with c3: thn_cari = st.text_input("Tahun", value=str(datetime.now().year))
        
        nipp_cari = opt_k[nama_cari]
        filter_bln = f"{thn_cari}-{bln_cari}"
        
        prof = supabase.table("karyawan").select("*").eq("nipp", nipp_cari).single().execute().data
        res_harian = supabase.table("laporan").select("*").eq("nipp", nipp_cari).gte("tanggal", f"{filter_bln}-01").lte("tanggal", f"{filter_bln}-31").order("tanggal").execute().data
        
        if res_harian:
            df = pd.DataFrame(res_harian)
            st.dataframe(df[["tanggal", "dinasan", "kegiatan", "serah_terima"]], use_container_width=True)
            
            if st.button("🖨️ Urutkan & Cetak PDF (Sesuai Format Template Gambar)"):
                pdf = FPDF()
                
                # ================= HALAMAN 1: COVER LAYOUT KANAN KERETA =================
                pdf.add_page()
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(100, 8, "LAPORAN KEGIATAN PENGOPERASIAN", ln=True)
                pdf.set_font("Arial", '', 11)
                pdf.cell(100, 8, f"BULAN: {filter_bln.upper()}", ln=True)
                pdf.ln(25)
                
                # Cetak Data Profil Karyawan di Sisi Kiri Halaman
                pdf.set_font("Arial", 'B', 10)
                labels = [("NAMA", prof['nama']), ("NIPP", prof['nipp']), ("JABATAN", prof['jabatan']), ("UNIT KERJA", prof['unit_kerja']), ("DAOP", prof['daop'])]
                for label, val in labels:
                    pdf.cell(30, 10, label, ln=False)
                    pdf.cell(5, 10, ":", ln=False)
                    pdf.set_font("Arial", '', 10)
                    pdf.cell(65, 10, str(val), ln=True)
                    pdf.set_font("Arial", 'B', 10)
                
                # Gambar Kereta Melintasi Jembatan di Sisi Kanan Cover (Seperti di Gambar)
                try:
                    # Menggunakan link ilustrasi lokomotif publik KAI yang stabil
                    url_kereta = "https://images.unsplash.com/photo-1532103054090-334e6e60b77a?q=80&w=600&auto=format&fit=crop"
                    res_k = requests.get(url_kereta)
                    pdf.image(BytesIO(res_k.content), x=110, y=35, w=85, h=130)
                except:
                    pass
                
                # ================= HALAMAN 2: FOTO SMARTCARD =================
                pdf.add_page()
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(200, 10, "FOTO SMARTCARD", ln=True, align='C')
                pdf.ln(10)
                if prof.get('smartcard_url'):
                    res = requests.get(prof['smartcard_url'])
                    pdf.image(BytesIO(res.content), x=25, y=40, w=160, h=100)
                else:
                    pdf.cell(200, 10, "[Belum ada lampiran Smartcard PKA]", align='C')
                
                # ================= HALAMAN 3: DAFTAR HADIR BULANAN =================
                pdf.add_page()
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(200, 10, f"DAFTAR HADIR BULAN {filter_bln}", ln=True, align='C')
                pdf.ln(10)
                abs_data = supabase.table("daftar_hadir").select("foto_hadir_url").eq("nipp", nipp_cari).eq("bulan_tahun", filter_bln).execute().data
                if abs_data and abs_data[0]['foto_hadir_url']:
                    res = requests.get(abs_data[0]['foto_hadir_url'])
                    pdf.image(BytesIO(res.content), x=12, y=35, w=186, h=140)
                else:
                    pdf.cell(200, 10, "[Belum ada lampiran Daftar Hadir Bulanan]", align='C')
                
                # ================= HALAMAN 4: TABEL STRUKTUR KRONOLOGIS =================
                pdf.add_page()
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(200, 10, "REKAPITULASI LAPORAN REAL-TIME", ln=True, align='C')
                pdf.ln(5)
                
                # Desain Header Kolom Sesuai Persis dengan Format Gambar Anda
                pdf.set_font("Arial", 'B', 9)
                pdf.cell(25, 10, "Hari / Tanggal", border=1, align='C')
                pdf.cell(42, 10, "Kegiatan", border=1, align='C')
                pdf.cell(48, 10, "Serah Terima Dinasan", border=1, align='C')
                pdf.cell(75, 10, "Dokumentasi Kegiatan", border=1, ln=True, align='C')
                
                pdf.set_font("Arial", '', 8)
                row_height = 32 # Tinggi baris kotak agar foto muat presisi di dalam tabel
                
                for r in res_harian:
                    # Cegah tabel terpotong di bawah kertas
                    if pdf.get_y() + row_height > 275:
                        pdf.add_page()
                        pdf.set_font("Arial", 'B', 9)
                        pdf.cell(25, 10, "Hari / Tanggal", border=1, align='C')
                        pdf.cell(42, 10, "Kegiatan", border=1, align='C')
                        pdf.cell(48, 10, "Serah Terima Dinasan", border=1, align='C')
                        pdf.cell(75, 10, "Dokumentasi Kegiatan", border=1, ln=True, align='C')
                        pdf.set_font("Arial", '', 8)

                    x = pdf.get_x()
                    y = pdf.get_y()
                    
                    # Kotak 1: Tanggal
                    pdf.rect(x, y, 25, row_height)
                    pdf.set_xy(x, y + 12)
                    pdf.cell(25, 5, str(r['tanggal']), border=0, align='C')
                    
                    # Kotak 2: Kegiatan (Multi-line text handling)
                    pdf.set_xy(x + 25, y + 2)
                    pdf.multi_cell(42, 5, str(r['kegiatan'])[:70], border=0, align='L')
                    pdf.rect(x + 25, y, 42, row_height)
                    
                    # Kotak 3: Serah Terima Dinasan
                    pdf.set_xy(x + 67, y + 2)
                    pdf.multi_cell(48, 5, str(r['serah_terima'])[:80], border=0, align='L')
                    pdf.rect(x + 67, y, 48, row_height)
                    
                    # Kotak 4: Dokumentasi Foto / Status Dinasan (Libur/Sakit)
                    pdf.rect(x + 115, y, 75, row_height)
                    if str(r['foto1_url']).startswith("http"):
                        try:
                            res1 = requests.get(r['foto1_url'])
                            pdf.image(BytesIO(res1.content), x=x+118, y=y+3, w=32, h=26)
                        except:
                            pdf.set_xy(x + 115, y + 12)
                            pdf.cell(35, 5, "[Gagal Load]", align='C')
                            
                        if str(r['foto2_url']).startswith("http"):
                            try:
                                res2 = requests.get(r['foto2_url'])
                                pdf.image(BytesIO(res2.content), x=x+154, y=y+3, w=32, h=26)
                            except:
                                pass
                    else:
                        # Jika status LIBUR/SAKIT, teks tercetak tepat di tengah kolom dokumentasi
                        pdf.set_font("Arial", 'B', 10)
                        pdf.set_xy(x + 115, y + 12)
                        pdf.cell(75, 5, str(r['foto1_url']), border=0, align='C')
                        pdf.set_font("Arial", '', 8)
                        
                    pdf.set_y(y + row_height)
                
                pdf_output = BytesIO()
                pdf.output(pdf_output)
                st.download_button(label="📥 Download Dokumen PDF Resmi 4 Halaman", data=pdf_output.getvalue(), file_name=f"Laporan_Resmi_{nama_cari}_{filter_bln}.pdf", mime="application/pdf")
        else:
            st.info("Belum ada entri data laporan untuk bulan ini.")
