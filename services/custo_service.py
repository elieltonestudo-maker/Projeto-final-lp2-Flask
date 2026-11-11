class CustoService:
    @staticmethod
    def calcular(martelo, quantidade, taxa_leilao, frete_total, total_subtotal_lote):
        """
        Regra única de cálculo de custo de uma cédula.
        O rateio do frete é feito com base no subtotal (martelo + taxa) do lote.
        Retorna um dicionário com valor_base, subtotal, rateio e custo_final.
        """
        # 1. Calcula o valor base (Martelo * Quantidade)
        valor_base = martelo * quantidade
        
        # 2. Calcula o subtotal (Martelo + Taxa)
        subtotal = valor_base + (valor_base * (taxa_leilao / 100))
        
        # 3. Calcula o rateio do frete com base no subtotal
        rateio = 0.0
        if total_subtotal_lote > 0:
            rateio = (subtotal / total_subtotal_lote) * frete_total
            
        # 4. Custo Final
        custo_final = subtotal + rateio
        
        return {
            'valor_base': valor_base,
            'subtotal': subtotal,
            'rateio': rateio,
            'custo_final': custo_final
        }