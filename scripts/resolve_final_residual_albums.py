#!/usr/bin/env python3
"""
resolve_final_residual_albums.py
Applies exact, verified metadata fixes for the final 28 residual albums in tamil_discography.db.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tamil_discography.db"

EXACT_FIXES = {
    # (id, title, year): (composer, cast)
    7919: ("M. S. Viswanathan, Joseph Krishna", "Muralidas, Gemini Ganesan, Thikkurissy Sukumaran Nair, Jayalalithaa, Jayabharathi, M. N. Nambiar"),
    7931: ("", "A. V. M. Rajan, Kumari Padmini, Pandari Bai"),
    8073: ("V. Kumar", "R. Muthuraman, Padmapriya, Kumari Padmini, Jayakumari"),
    8172: ("", "Thengai Srinivasan, P. R. Varalakshmi"),
    8193: ("G. Devarajan", "Kamal Haasan, Sridevi, Adoor Bhasi, Thikkurissy Sukumaran Nair, Kaviyoor Ponnamma, Sankaradi"),
    8294: ("", "Delhi Ganesh, Jamila"),
    8382: ("Shankar–Ganesh", "Delhi Ganesh, Rajani"),
    8450: ("A. V. Ramanan", "Vijayakanth, Thirumurugan, Padmapriya, Praveena"),
    8455: ("Shankar–Ganesh", "Thirumurugan, M. S. Vasanthi, Meera, Y. G. Mahendra, Sukumari"),
    8497: ("Vijaya Ramani", "Thirumurugan, Vadivukkarasi, M. S. Vasanthi"),
    8782: ("", "Nizhalgal Ravi, Anand Babu, Nassar, Silk Smitha, Surekha, Sindhu, Meenakshi"),
    9342: ("", "Chandrasekhar, Senthil"),
    9391: ("Shankar–Ganesh", "Rajesh, Nizhalgal Ravi, Murali, B. Saroja Devi, Divya, Indira, S. S. Chandran, Manorama, Vinu Chakravarthy, Malaysia Vasudevan, Vennira Aadai Moorthy, Chinni Jayanth, Disco Shanti, Charle"),
    9465: ("Shyam", "Pandiarajan, Chithra, Y. G. Mahendra"),
    4039: ("Sathish Ramalingam", "Jay Srinivasa Kumar, Vasundhara Kashyap"),
    4270: ("Kathaka Thirumavalavan", "Karthik Jai"),
    4778: ("Anthony", "Ashok, Anvitha"),
    4329: ("Albons", "Anbumani, Sathishkumar Gopalakrishnan, Vasanthakumar Ramukutty"),
    4332: ("J. Nazim", "V. S. Vijayagopal, Vishnu Priya"),
    5867: ("Jayamurugesan", "Abishek Kumaran, Anupriya, Bose Venkat"),
    6024: ("Vijay Prabhu", "Kavithiran, Madhumitha, Appukutty, Mime Gopi"),
    6216: ("Ilaiyaraaja", "Harikumar, Maadhavi Latha, M. S. Bhaskar"),
    6291: ("Karthik Krishnan", "Dhakshan Vijay, Mime Gopi, Gayathri"),
    6310: ("Karan B. Krupa", "Kaakkaa Muttai Ramesh, J. Vignesh, Velmurugan, Manobala"),
    6571: ("M. L. R. Karthikeyan", "Ananda Kumar, Jesi Rathnavathy, Shanmuga Sundaram"),
    6587: ("Jagadeesh Kumar", "Poovarasan, Saravanan, Vela Ramamoorthy"),
    10040: ("Sajid–Wajid", "Salman Khan, Ayesha Takia, Prakash Raj, Vinod Khanna"),
    7135: ("Devi Sri Prasad", "Parvati Nair, Ganesh Venkatraman, Master Mahendran"),
}

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for aid, (comp, cast) in EXACT_FIXES.items():
        c.execute('UPDATE albums SET composer = ?, "cast" = ? WHERE id = ?', (comp, cast, aid))
        print(f"Fixed album {aid}: Composer='{comp}' | Cast='{cast[:30]}...'")

    conn.commit()
    conn.close()
    print("Done applying final residual album fixes.")

if __name__ == "__main__":
    main()
