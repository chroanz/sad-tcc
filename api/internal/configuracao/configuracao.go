// Package configuracao lê as variáveis de ambiente descritas em .env.exemplo.
package configuracao

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"
)

// Configuracao reúne todos os parâmetros externos da API. É montada uma vez em
// cmd/servidor e injetada nas demais camadas — nenhum outro pacote lê
// os.Getenv diretamente.
type Configuracao struct {
	PortaAPI              string
	BancoURL              string
	OtimizadorURL         string
	OtimizadorTempoLimite time.Duration
	JWTSegredo            string
	JWTValidade           time.Duration
	AplicarMigracoes      bool
	OrigemPadraoLatitude  float64
	OrigemPadraoLongitude float64
}

// Carregar lê o ambiente e aplica os padrões de .env.exemplo. BANCO_URL e
// JWT_SEGREDO não têm padrão: a ausência de qualquer um deles é erro fatal na
// inicialização.
func Carregar() (Configuracao, error) {
	cfg := Configuracao{
		PortaAPI:      texto("API_PORTA", "8080"),
		BancoURL:      texto("BANCO_URL", ""),
		OtimizadorURL: strings.TrimRight(texto("OTIMIZADOR_URL", "http://localhost:8001"), "/"),
		JWTSegredo:    texto("JWT_SEGREDO", ""),
	}

	if cfg.BancoURL == "" {
		return Configuracao{}, fmt.Errorf("variável de ambiente BANCO_URL é obrigatória")
	}
	if cfg.JWTSegredo == "" {
		return Configuracao{}, fmt.Errorf("variável de ambiente JWT_SEGREDO é obrigatória")
	}

	segundos, err := inteiro("OTIMIZADOR_TIMEOUT_SEGUNDOS", 30)
	if err != nil {
		return Configuracao{}, err
	}
	if segundos <= 0 {
		return Configuracao{}, fmt.Errorf("OTIMIZADOR_TIMEOUT_SEGUNDOS deve ser maior que zero")
	}
	cfg.OtimizadorTempoLimite = time.Duration(segundos) * time.Second

	horas, err := inteiro("JWT_HORAS_VALIDADE", 24)
	if err != nil {
		return Configuracao{}, err
	}
	if horas <= 0 {
		return Configuracao{}, fmt.Errorf("JWT_HORAS_VALIDADE deve ser maior que zero")
	}
	cfg.JWTValidade = time.Duration(horas) * time.Hour

	cfg.AplicarMigracoes, err = booleano("APLICAR_MIGRACOES", true)
	if err != nil {
		return Configuracao{}, err
	}

	cfg.OrigemPadraoLatitude, err = decimal("ORIGEM_PADRAO_LATITUDE", -7.213100)
	if err != nil {
		return Configuracao{}, err
	}
	cfg.OrigemPadraoLongitude, err = decimal("ORIGEM_PADRAO_LONGITUDE", -39.315300)
	if err != nil {
		return Configuracao{}, err
	}
	if cfg.OrigemPadraoLatitude < -90 || cfg.OrigemPadraoLatitude > 90 {
		return Configuracao{}, fmt.Errorf("ORIGEM_PADRAO_LATITUDE fora de [-90, 90]")
	}
	if cfg.OrigemPadraoLongitude < -180 || cfg.OrigemPadraoLongitude > 180 {
		return Configuracao{}, fmt.Errorf("ORIGEM_PADRAO_LONGITUDE fora de [-180, 180]")
	}

	return cfg, nil
}

func texto(chave, padrao string) string {
	if valor := strings.TrimSpace(os.Getenv(chave)); valor != "" {
		return valor
	}
	return padrao
}

func inteiro(chave string, padrao int) (int, error) {
	bruto := strings.TrimSpace(os.Getenv(chave))
	if bruto == "" {
		return padrao, nil
	}
	valor, err := strconv.Atoi(bruto)
	if err != nil {
		return 0, fmt.Errorf("ler %s: %w", chave, err)
	}
	return valor, nil
}

func decimal(chave string, padrao float64) (float64, error) {
	bruto := strings.TrimSpace(os.Getenv(chave))
	if bruto == "" {
		return padrao, nil
	}
	valor, err := strconv.ParseFloat(bruto, 64)
	if err != nil {
		return 0, fmt.Errorf("ler %s: %w", chave, err)
	}
	return valor, nil
}

func booleano(chave string, padrao bool) (bool, error) {
	bruto := strings.TrimSpace(os.Getenv(chave))
	if bruto == "" {
		return padrao, nil
	}
	valor, err := strconv.ParseBool(bruto)
	if err != nil {
		return false, fmt.Errorf("ler %s: %w", chave, err)
	}
	return valor, nil
}
