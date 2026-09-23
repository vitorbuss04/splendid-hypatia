import io
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm

def build_pdf_document(
    project_data: dict,
    user_data: dict,
    doc_type: str = "client"
) -> io.BytesIO:
    """
    Builds a professional PDF document.
    doc_type:
      - 'client': Commercial quote for the customer
      - 'technical': Internal production worksheet
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )

    styles = getSampleStyleSheet()
    
    # Custom color palette: Modern Slate & Vibrant Blue
    PRIMARY = colors.HexColor("#1e293b")  # Dark Slate
    ACCENT = colors.HexColor("#2563eb")   # Royal Blue
    ACCENT_LIGHT = colors.HexColor("#eff6ff")
    TEXT_MUTED = colors.HexColor("#64748b")
    BORDER_COLOR = colors.HexColor("#e2e8f0")
    BG_LIGHT = colors.HexColor("#f8fafc")
    SUCCESS = colors.HexColor("#059669")

    # Typography styles
    style_header_company = ParagraphStyle(
        "HeaderCompany",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=PRIMARY,
    )
    style_header_sub = ParagraphStyle(
        "HeaderSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=TEXT_MUTED,
    )
    style_doc_title = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        alignment=2,  # Right
        textColor=ACCENT,
    )
    style_doc_num = ParagraphStyle(
        "DocNum",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        alignment=2,  # Right
        textColor=TEXT_MUTED,
    )
    style_section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=PRIMARY,
        spaceBefore=8,
        spaceAfter=4,
    )
    style_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=PRIMARY,
    )
    style_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=PRIMARY,
    )
    style_cell_right = ParagraphStyle(
        "TableCellRight",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=2,
        textColor=PRIMARY,
    )
    style_cell_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    )
    style_cell_header_right = ParagraphStyle(
        "TableHeaderRight",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        alignment=2,
        textColor=colors.white,
    )

    story = []

    # 1. Header with Company & Document Info
    company_name = user_data.get("company_name") or user_data.get("full_name") or "Serviços de Impressão 3D"
    contact_parts = []
    if user_data.get("phone"):
        contact_parts.append(f"Tel: {user_data['phone']}")
    if user_data.get("email"):
        contact_parts.append(f"E-mail: {user_data['email']}")
    contact_text = " | ".join(contact_parts) if contact_parts else "Projetos e Prototipagem Rápida em Manufatura Aditiva"

    doc_name = "ORÇAMENTO COMERCIAL" if doc_type == "client" else "FICHA TÉCNICA DE PRODUÇÃO"
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_str = now_utc.strftime("%d/%m/%Y")
    valid_str = (now_utc + datetime.timedelta(days=15)).strftime("%d/%m/%Y")
    quote_code = f"#{project_data.get('id', 1):04d}"

    header_table_data = [
        [
            Paragraph(company_name, style_header_company),
            Paragraph(doc_name, style_doc_title),
        ],
        [
            Paragraph(contact_text, style_header_sub),
            Paragraph(f"Orçamento: <b>{quote_code}</b> | Emissão: {now_str}", style_doc_num),
        ],
    ]
    if doc_type == "client":
        header_table_data.append([
            Paragraph("", style_header_sub),
            Paragraph(f"Validade da Proposta: {valid_str}", style_doc_num),
        ])

    header_table = Table(header_table_data, colWidths=[110 * mm, 72 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceAfter=8))

    # 2. Client & Project Details Box
    client_name = project_data.get("client_name") or "Cliente não informado"
    client_email = project_data.get("client_email") or "—"
    client_phone = project_data.get("client_phone") or "—"
    project_title = project_data.get("name") or "Projeto sem título"

    info_data = [
        [
            Paragraph(f"<b>Projeto:</b> {project_title}", style_cell),
            Paragraph(f"<b>Cliente:</b> {client_name}", style_cell),
        ],
        [
            Paragraph(f"<b>Status:</b> {project_data.get('status', 'draft').upper()}", style_cell),
            Paragraph(f"<b>Contato:</b> {client_phone} | {client_email}", style_cell),
        ]
    ]
    info_table = Table(info_data, colWidths=[91 * mm, 91 * mm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 4 * mm))

    summary = project_data.get("summary", {})
    plates_details = summary.get("plates_details", [])
    bom_details = summary.get("bom_details", [])

    # 3. Content depending on Document Type
    if doc_type == "client":
        # CLIENT QUOTE VIEW
        story.append(Paragraph("1. ITENS FABRICADOS EM IMPRESSÃO 3D", style_section_title))

        plate_table_data = [[
            Paragraph("Item / Descrição", style_cell_header),
            Paragraph("Material / Acabamento", style_cell_header),
            Paragraph("Qtd", style_cell_header_right),
            Paragraph("Tempo Estimado", style_cell_header_right),
        ]]

        if not plates_details:
            plate_table_data.append([
                Paragraph("Nenhuma peça impressa configurada", style_cell),
                Paragraph("—", style_cell),
                Paragraph("0", style_cell_right),
                Paragraph("—", style_cell_right),
            ])
        else:
            for p in plates_details:
                plate_table_data.append([
                    Paragraph(f"<b>{p.get('name', 'Placa')}</b>", style_cell),
                    Paragraph(p.get("filament_name", "Filamento Técnico"), style_cell),
                    Paragraph(str(p.get("quantity", 1)), style_cell_right),
                    Paragraph(f"{p.get('total_time_hours', 0.0):.1f} h", style_cell_right),
                ])

        plate_table = Table(plate_table_data, colWidths=[65 * mm, 52 * mm, 25 * mm, 40 * mm])
        plate_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ]))
        story.append(plate_table)
        story.append(Spacer(1, 4 * mm))

        # BOM Items if present
        if bom_details:
            story.append(Paragraph("2. COMPONENTES E ACESSÓRIOS ADICIONAIS (BOM)", style_section_title))
            bom_table_data = [[
                Paragraph("Componente", style_cell_header),
                Paragraph("Categoria", style_cell_header),
                Paragraph("Qtd", style_cell_header_right),
                Paragraph("Subtotal", style_cell_header_right),
            ]]
            for b in bom_details:
                bom_table_data.append([
                    Paragraph(b.get("name", "Componente"), style_cell),
                    Paragraph(b.get("category", "Geral"), style_cell),
                    Paragraph(str(b.get("quantity", 1)), style_cell_right),
                    Paragraph(f"R$ {b.get('subtotal', 0.0):.2f}", style_cell_right),
                ])
            bom_table = Table(bom_table_data, colWidths=[75 * mm, 42 * mm, 25 * mm, 40 * mm])
            bom_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ]))
            story.append(bom_table)
            story.append(Spacer(1, 4 * mm))

        # Services / Labor if present
        cad_hours = summary.get("cad_hours", 0)
        post_hours = summary.get("post_hours", 0)
        if cad_hours > 0 or post_hours > 0:
            story.append(Paragraph("3. ENGENHARIA E SERVIÇOS TÉCNICOS", style_section_title))
            srv_table_data = [[
                Paragraph("Serviço", style_cell_header),
                Paragraph("Descrição", style_cell_header),
                Paragraph("Tempo", style_cell_header_right),
            ]]
            if cad_hours > 0:
                srv_table_data.append([
                    Paragraph("Modelagem CAD / Ajuste 3D", style_cell_bold),
                    Paragraph("Desenvolvimento e otimização geométrica para manufatura", style_cell),
                    Paragraph(f"{cad_hours:.1f} h", style_cell_right),
                ])
            if post_hours > 0:
                srv_table_data.append([
                    Paragraph("Pós-processamento Manual", style_cell_bold),
                    Paragraph("Remoção de suportes, lixamento, inserção de insertos e acabamento", style_cell),
                    Paragraph(f"{post_hours:.1f} h", style_cell_right),
                ])
            srv_table = Table(srv_table_data, colWidths=[65 * mm, 82 * mm, 35 * mm])
            srv_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ]))
            story.append(srv_table)
            story.append(Spacer(1, 4 * mm))

        # 4. Financial Summary & Total Box
        story.append(Paragraph("RESUMO FINANCEIRO DA PROPOSTA", style_section_title))

        subtotal_price = summary.get("suggested_price", 0.0)
        discount_amount = summary.get("discount_amount", 0.0)
        discount_percent = summary.get("discount_percent", 0.0)
        shipping_cost = summary.get("shipping_cost", 0.0)
        final_price = summary.get("final_price_to_client", 0.0)

        fin_rows = [
            [Paragraph("Subtotal dos Itens e Serviços:", style_cell_bold), Paragraph(f"R$ {subtotal_price:.2f}", style_cell_right)]
        ]
        if discount_amount > 0:
            fin_rows.append([
                Paragraph(f"Desconto Comercial ({discount_percent:.1f}%):", style_cell),
                Paragraph(f"- R$ {discount_amount:.2f}", style_cell_right)
            ])
        if shipping_cost > 0:
            fin_rows.append([
                Paragraph("Frete / Envio:", style_cell),
                Paragraph(f"+ R$ {shipping_cost:.2f}", style_cell_right)
            ])
        fin_rows.append([
            Paragraph("<b>TOTAL GERAL DA PROPOSTA:</b>", ParagraphStyle("BigTot", parent=style_cell_bold, fontSize=12, leading=15, textColor=ACCENT)),
            Paragraph(f"<b>R$ {final_price:.2f}</b>", ParagraphStyle("BigTotVal", parent=style_cell_right, fontSize=13, leading=15, textColor=ACCENT)),
        ])

        fin_table = Table(fin_rows, colWidths=[120 * mm, 62 * mm])
        fin_table.setStyle(TableStyle([
            ('BACKGROUND', (0, -1), (-1, -1), ACCENT_LIGHT),
            ('BOX', (0, 0), (-1, -1), 1, ACCENT),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(fin_table)
        story.append(Spacer(1, 5 * mm))

        # 5. Terms & Payment Info Box
        pix_info = user_data.get("pix_key")
        terms_text = f"""<b>Condições de Pagamento:</b> A combinar / 50% na aprovação e 50% na entrega.<br/>
{f'<b>Chave PIX:</b> {pix_info}<br/>' if pix_info else ''}
<b>Prazo de Produção:</b> Estimado em até {max(1, int(summary.get('total_print_time_hours', 1) / 8) + 1)} dias úteis após confirmação.<br/>
<b>Garantia:</b> Garantia de fabricação contra defeitos dimensionais ou delaminação de camadas conforme especificações acordadas."""
        
        terms_p = Paragraph(terms_text, ParagraphStyle("Terms", parent=styles["Normal"], fontSize=8.5, leading=12, textColor=PRIMARY))
        terms_table = Table([[terms_p]], colWidths=[182 * mm])
        terms_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(terms_table)

    else:
        # TECHNICAL PRODUCTION WORKSHEET VIEW
        story.append(Paragraph("1. PARÂMETROS OPERACIONAIS DE PRODUÇÃO (PLACAS)", style_section_title))

        tech_table_data = [[
            Paragraph("Placa", style_cell_header),
            Paragraph("Impressora", style_cell_header),
            Paragraph("Filamento", style_cell_header),
            Paragraph("Tempo Unit.", style_cell_header_right),
            Paragraph("Peso Peça", style_cell_header_right),
            Paragraph("Purga", style_cell_header_right),
            Paragraph("Qtd", style_cell_header_right),
            Paragraph("Tempo Total", style_cell_header_right),
        ]]

        for p in plates_details:
            tech_table_data.append([
                Paragraph(f"<b>{p.get('name', 'Placa')}</b>", style_cell),
                Paragraph(p.get("printer_name", "Padrão"), style_cell),
                Paragraph(p.get("filament_name", "Padrão"), style_cell),
                Paragraph(f"{p.get('unit_print_time_hours', 0.0):.1f} h", style_cell_right),
                Paragraph(f"{p.get('unit_raw_weight_g', 0.0):.1f} g", style_cell_right),
                Paragraph(f"{p.get('purge_weight_g', 0.0):.1f} g", style_cell_right),
                Paragraph(str(p.get("quantity", 1)), style_cell_right),
                Paragraph(f"{p.get('total_time_hours', 0.0):.1f} h", style_cell_right),
            ])

        tech_table = Table(tech_table_data, colWidths=[36*mm, 28*mm, 28*mm, 18*mm, 18*mm, 16*mm, 14*mm, 24*mm])
        tech_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ]))
        story.append(tech_table)
        story.append(Spacer(1, 4 * mm))

        # Checklist BOM
        if bom_details:
            story.append(Paragraph("2. CHECKLIST DE MONTAGEM E INSUMOS (BOM)", style_section_title))
            chk_table_data = [[
                Paragraph("Item Insumo", style_cell_header),
                Paragraph("Categoria", style_cell_header),
                Paragraph("Qtd Requerida", style_cell_header_right),
                Paragraph("Conferência [ OK ]", style_cell_header_right),
            ]]
            for b in bom_details:
                chk_table_data.append([
                    Paragraph(b.get("name", "Item"), style_cell),
                    Paragraph(b.get("category", "Geral"), style_cell),
                    Paragraph(str(b.get("quantity", 1)), style_cell_right),
                    Paragraph("[  ] Conferido", style_cell_right),
                ])
            chk_table = Table(chk_table_data, colWidths=[70 * mm, 45 * mm, 32 * mm, 35 * mm])
            chk_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
                ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ]))
            story.append(chk_table)
            story.append(Spacer(1, 4 * mm))

        # Internal Cost breakdown for Owner/Operator
        story.append(Paragraph("3. DEMONSTRATIVO DE CUSTOS INTERNOS E MARGENS", style_section_title))
        cost_breakdown_data = [
            [Paragraph("Consumo Total de Filamento:", style_cell), Paragraph(f"{summary.get('total_filament_weight_g', 0.0):.1f} g (R$ {summary.get('total_material_cost', 0.0):.2f})", style_cell_right)],
            [Paragraph("Tempo Total de Máquina:", style_cell), Paragraph(f"{summary.get('total_print_time_hours', 0.0):.1f} h (R$ {summary.get('total_machine_cost', 0.0):.2f})", style_cell_right)],
            [Paragraph("Energia Elétrica Estimada:", style_cell), Paragraph(f"R$ {summary.get('total_energy_cost', 0.0):.2f}", style_cell_right)],
            [Paragraph("Depreciação de Máquina:", style_cell), Paragraph(f"R$ {summary.get('total_depreciation_cost', 0.0):.2f}", style_cell_right)],
            [Paragraph("Reserva de Manutenção:", style_cell), Paragraph(f"R$ {summary.get('total_maintenance_cost', 0.0):.2f}", style_cell_right)],
            [Paragraph("Custo Total BOM / Insumos:", style_cell), Paragraph(f"R$ {summary.get('total_bom_cost', 0.0):.2f}", style_cell_right)],
            [Paragraph("Mão de Obra (CAD + Pós):", style_cell), Paragraph(f"R$ {summary.get('total_labor_cost', 0.0):.2f}", style_cell_right)],
            [Paragraph("Custos Indiretos / Overhead:", style_cell), Paragraph(f"R$ {summary.get('overhead_cost', 0.0):.2f}", style_cell_right)],
            [Paragraph("<b>Custo Base Total:</b>", style_cell_bold), Paragraph(f"<b>R$ {summary.get('base_cost', 0.0):.2f}</b>", style_cell_right)],
            [Paragraph("Margem de Lucro Alvo:", style_cell), Paragraph(f"{summary.get('profit_margin_percent', 0.0):.1f}%", style_cell_right)],
            [Paragraph("Alíquota Impostos / Taxas:", style_cell), Paragraph(f"{summary.get('tax_rate_percent', 0.0):.1f}% (R$ {summary.get('tax_amount', 0.0):.2f})", style_cell_right)],
            [Paragraph("<b>Preço Final de Venda Sugerido:</b>", ParagraphStyle("PB", parent=style_cell_bold, textColor=ACCENT)), Paragraph(f"<b>R$ {summary.get('final_price_to_client', 0.0):.2f}</b>", ParagraphStyle("PR", parent=style_cell_right, textColor=ACCENT))],
            [Paragraph("<b>Lucro Líquido Real Estimado:</b>", ParagraphStyle("LB", parent=style_cell_bold, textColor=SUCCESS)), Paragraph(f"<b>R$ {summary.get('net_profit', 0.0):.2f} ({summary.get('effective_profit_margin_percent', 0.0):.1f}%)</b>", ParagraphStyle("LR", parent=style_cell_right, textColor=SUCCESS))],
        ]
        cost_table = Table(cost_breakdown_data, colWidths=[110 * mm, 72 * mm])
        cost_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(cost_table)

    # Footer note
    story.append(Spacer(1, 6 * mm))
    notes_txt = project_data.get("notes")
    if notes_txt:
        notes_p = Paragraph(f"<b>Observações do Projeto:</b><br/>{notes_txt}", style_cell)
        story.append(notes_p)
        story.append(Spacer(1, 3 * mm))

    footer_time = datetime.datetime.now(datetime.timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    footer_p = Paragraph(f"Documento gerado automaticamente pelo Sistema de Gestao e Precificacao 3D em {footer_time}", style_header_sub)
    story.append(footer_p)

    doc.build(story)
    buffer.seek(0)
    return buffer
