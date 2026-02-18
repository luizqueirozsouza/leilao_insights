import { useState, useEffect } from "react";
import axios from "axios";
import Select from "react-select";
import {
  Home,
  MapPin,
  ExternalLink,
  Filter,
  Globe,
  AlertCircle,
  Loader2,
  Tag,
  X,
  Search,
  Percent,
  ArrowUpDown,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:3001/api";

interface Property {
  uf: string;
  numero_imovel: string;
  payload: {
    Cidade: string;
    Bairro: string;
    Endereço: string;
    Preço: string;
    "Valor de avaliação": string;
    Desconto: string;
    "Link de acesso": string;
    "Modalidade de venda": string;
    "Nº do imóvel": string;
    Descrição?: string;
  };
}

const customSelectStyles = {
  control: (base: any, state: any) => ({
    ...base,
    backgroundColor: "#ffffff",
    borderColor: state.isFocused ? "#2563eb" : "#e2e8f0",
    borderRadius: "1rem",
    padding: "4px",
    fontSize: "11px",
    fontWeight: "700",
    color: "#1e293b",
    boxShadow: state.isFocused ? "0 0 0 2px rgba(37,99,235,0.1)" : "none",
    "&:hover": {
      borderColor: "#cbd5e1",
    },
  }),
  menu: (base: any) => ({
    ...base,
    backgroundColor: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: "1rem",
    overflow: "hidden",
    zIndex: 9999,
    boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.1)",
  }),
  menuPortal: (base: any) => ({ ...base, zIndex: 9999 }),
  option: (base: any, state: any) => ({
    ...base,
    backgroundColor: state.isFocused ? "#f1f5f9" : "transparent",
    color: state.isSelected ? "#2563eb" : "#1e293b",
    fontSize: "11px",
    fontWeight: "700",
    textTransform: "uppercase",
    "&:active": {
      backgroundColor: "#e2e8f0",
    },
  }),
  multiValue: (base: any) => ({
    ...base,
    backgroundColor: "#eff6ff",
    borderRadius: "0.5rem",
    border: "1px solid #dbeafe",
  }),
  multiValueLabel: (base: any) => ({
    ...base,
    color: "#2563eb",
    fontSize: "10px",
    fontWeight: "900",
  }),
  multiValueRemove: (base: any) => ({
    ...base,
    color: "#2563eb",
    "&:hover": {
      backgroundColor: "#2563eb",
      color: "white",
    },
  }),
  input: (base: any) => ({
    ...base,
    color: "#1e293b",
  }),
  singleValue: (base: any) => ({
    ...base,
    color: "#1e293b",
    textTransform: "uppercase",
  }),
  placeholder: (base: any) => ({
    ...base,
    color: "#94a3b8",
    textTransform: "uppercase",
  }),
};

const MultiFilterSelect = ({
  label,
  value,
  options = [],
  onChange,
  icon: Icon,
  disabled,
  loading,
  isMulti = true,
}: any) => {
  const selectOptions = options.map((opt: any) => ({
    value: opt.value,
    label: `${opt.label.toUpperCase()} (${opt.count})`,
  }));

  const defaultValue = isMulti
    ? value
      ? value.split(",").map((v: string) => {
          const found = options.find((o: any) => o.value === v);
          return {
            value: v,
            label: found
              ? `${found.label.toUpperCase()} (${found.count})`
              : v.toUpperCase(),
          };
        })
      : []
    : value
      ? (() => {
          const found = options.find((o: any) => o.value === value);
          return {
            value: value,
            label: found
              ? `${found.label.toUpperCase()} (${found.count})`
              : value.toUpperCase(),
          };
        })()
      : null;

  return (
    <div
      className={`flex flex-col gap-1.5 flex-1 min-w-[200px] ${disabled ? "opacity-40 cursor-not-allowed" : ""}`}
    >
      <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1 flex items-center gap-1.5">
        {Icon && <Icon className="w-3 h-3 text-blue-600" />} {label}
        {loading && <Loader2 className="w-2.5 h-2.5 animate-spin" />}
      </label>
      <Select
        isMulti={isMulti}
        placeholder={`SELECIONE (${label})`}
        options={selectOptions}
        value={defaultValue}
        onChange={(val: any) => {
          if (isMulti) {
            onChange(val ? val.map((v: any) => v.value).join(",") : "");
          } else {
            onChange(val ? val.value : "");
          }
        }}
        isDisabled={disabled}
        isLoading={loading}
        styles={customSelectStyles}
        menuPortalTarget={document.body}
        noOptionsMessage={() => "NENHUMA OPÇÃO"}
      />
    </div>
  );
};

const PropertyCard = ({ property }: { property: Property }) => {
  const { payload, uf, numero_imovel } = property;
  const [imgError, setImgError] = useState(false);
  const imageUrl = `https://venda-imoveis.caixa.gov.br/fotos/F${numero_imovel}21.jpg`;

  const getRooms = (desc?: string) => {
    if (!desc) return null;
    const match = desc.match(/(\d+)\s*Quarto/i);
    return match ? match[1] : null;
  };

  const getGarage = (desc?: string) => {
    if (!desc) return null;
    const match = desc.match(/(\d+)\s*(Vaga|Garagem)/i);
    return match ? match[1] : "0";
  };

  const getArea = (desc?: string) => {
    if (!desc) return null;
    const match = desc.match(/(\d+[.,]\d+)\s*de\s*área\s*(privativa|total)/i);
    return match ? match[1] : null;
  };

  const getMatricula = (desc?: string) => {
    if (!desc) return null;
    const match = desc.match(/Matr[íi]cula(?:\(s\))?:\s*([A-Z0-9.\-\/]+)/i);
    return match ? match[1] : null;
  };

  const getInscricao = (desc?: string) => {
    if (!desc) return null;
    const match = desc.match(
      /Inscri[çc][ãa]o\s+imobili[áa]ria:\s*([A-Z0-9.\-\/]+)/i,
    );
    return match ? match[1] : null;
  };

  const getTipo = (desc?: string) => {
    if (!desc) return null;
    // Tenta formato detalhado
    const matchLabel = desc.match(/Tipo\s+de\s+im[óo]vel:\s*([^,.\n\r]+)/i);
    if (matchLabel) return matchLabel[1].trim();

    // Tenta formato simples do CSV (primeira palavra/frase antes da vírgula)
    const firstPart = desc.split(",")[0].trim();
    if (firstPart && firstPart.length < 30) return firstPart;

    return null;
  };

  const rooms = getRooms(payload.Descrição);
  const area = getArea(payload.Descrição);
  const garage = getGarage(payload.Descrição);
  const matricula = getMatricula(payload.Descrição);
  const inscricao = getInscricao(payload.Descrição);
  const tipo = getTipo(payload.Descrição);

  const hasFGTS = payload.Descrição?.toLocaleUpperCase().includes("FGTS");

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card rounded-[2.5rem] overflow-hidden flex flex-col group h-full border border-slate-200 hover:border-blue-500/30 transition-all duration-500 bg-white"
    >
      <div className="relative h-60 w-full overflow-hidden bg-slate-100">
        {!imgError ? (
          <img
            src={imageUrl}
            alt={numero_imovel}
            className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center bg-slate-50 text-slate-300">
            <Home className="w-10 h-10 opacity-20" />
            <span className="text-[8px] font-black uppercase tracking-widest mt-2 opacity-40">
              Sem Foto Disponível
            </span>
          </div>
        )}

        {/* Badges Principais */}
        <div className="absolute top-4 left-4 flex flex-col gap-2">
          <div className="flex gap-2">
            <span className="px-3 py-1 bg-blue-600 text-white text-[9px] font-black rounded-lg shadow-lg uppercase tracking-wider">
              {uf}
            </span>
            {payload.Desconto && (
              <div className="flex items-center gap-1.5 px-3 py-1 bg-emerald-500 text-white text-[10px] font-black rounded-lg shadow-lg">
                <Percent className="w-3 h-3" />
                {payload.Desconto}% ECONÔMICO
              </div>
            )}
          </div>
          <div className="flex gap-2">
            {hasFGTS && (
              <span className="w-fit px-3 py-1 bg-orange-500 text-white text-[8px] font-black rounded-lg shadow-lg uppercase tracking-tight italic">
                Aceita FGTS
              </span>
            )}
            {tipo && (
              <span className="w-fit px-3 py-1 bg-slate-800 text-white text-[8px] font-black rounded-lg shadow-lg uppercase tracking-widest">
                {tipo}
              </span>
            )}
          </div>
        </div>

        {/* Overlay de Informações Técnicas */}
        <div className="absolute bottom-4 left-4 right-4 flex gap-2">
          {rooms && (
            <div className="flex-1 bg-white/80 backdrop-blur-md border border-white/40 rounded-xl p-2.5 flex items-center justify-center gap-2 shadow-sm border-b-2 border-b-blue-500/20">
              <span className="text-slate-900 font-black text-xs">{rooms}</span>
              <span className="text-[8px] text-slate-500 font-bold uppercase">
                Quartos
              </span>
            </div>
          )}
          <div className="flex-1 bg-white/80 backdrop-blur-md border border-white/40 rounded-xl p-2.5 flex items-center justify-center gap-2 shadow-sm border-b-2 border-b-blue-500/20">
            <span className="text-slate-900 font-black text-xs">{garage}</span>
            <span className="text-[8px] text-slate-500 font-bold uppercase">
              Vagas
            </span>
          </div>
          {area && parseFloat(area) > 0 && (
            <div className="flex-1 bg-white/80 backdrop-blur-md border border-white/40 rounded-xl p-2.5 flex items-center justify-center gap-2 shadow-sm border-b-2 border-b-blue-500/20">
              <span className="text-slate-900 font-black text-xs">{area}</span>
              <span className="text-[8px] text-slate-500 font-bold uppercase">
                m²
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="p-6 space-y-6 flex-1">
        {/* Cabeçalho do Card */}
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <h4 className="text-slate-950 font-black text-xl uppercase line-clamp-1 leading-tight tracking-tight mb-1">
              {payload.Cidade}
            </h4>
            <div className="flex items-center gap-2">
              <span className="bg-blue-50 text-blue-600 text-[8px] font-black px-2 py-0.5 rounded-md uppercase tracking-widest">
                {payload["Modalidade de venda"]}
              </span>
            </div>
          </div>
        </div>

        {/* Detalhes Técnicos e Localização */}
        <div className="grid grid-cols-1 gap-4 bg-slate-50/50 p-4 rounded-2xl border border-slate-100">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-xl bg-blue-100/50 flex items-center justify-center shrink-0">
              <MapPin className="w-4 h-4 text-blue-600" />
            </div>
            <div className="text-[10px] leading-tight">
              <p className="text-slate-900 font-black uppercase mb-1">
                {payload.Bairro}
              </p>
              <p className="text-slate-500 font-medium line-clamp-2">
                {payload.Endereço}
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-200/50 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-bold text-slate-400 uppercase">
                Nº do Imóvel
              </span>
              <span className="text-[10px] font-black text-slate-700 font-mono">
                {payload["Nº do imóvel"]}
              </span>
            </div>
            {matricula && (
              <div className="flex items-center justify-between">
                <span className="text-[9px] font-bold text-slate-400 uppercase">
                  Matrícula
                </span>
                <span className="text-[10px] font-black text-blue-600 font-mono">
                  {matricula}
                </span>
              </div>
            )}
            {inscricao && (
              <div className="flex items-center justify-between">
                <span className="text-[9px] font-bold text-slate-400 uppercase">
                  Inscrição Imob.
                </span>
                <span className="text-[10px] font-black text-blue-600 font-mono">
                  {inscricao}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* SEÇÃO FINANCEIRA - DESTAQUE TOTAL */}
        <div className="space-y-3">
          {/* Valor de Avaliação com mais destaque */}
          <div className="bg-slate-900 rounded-2xl p-4 shadow-xl shadow-slate-200 relative overflow-hidden group/price">
            <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/10 rounded-full -mr-12 -mt-12 transition-transform group-hover/price:scale-150" />

            <div className="flex justify-between items-center mb-3 border-b border-white/10 pb-2">
              <span className="text-white text-[9px] font-black uppercase tracking-widest opacity-80">
                Valor de Avaliação
              </span>
              <span className="text-white font-black text-xs line-through italic decoration-white/30">
                R$ {payload["Valor de avaliação"]}
              </span>
            </div>

            <div>
              <p className="text-emerald-400 text-[10px] font-black uppercase tracking-tighter mb-1">
                Mínimo para lance
              </p>
              <div className="flex items-baseline gap-1">
                <span className="text-white font-black text-3xl tracking-tighter">
                  R$ {payload.Preço}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Descrição em Itálico */}
        {payload.Descrição && (
          <div className="px-1 border-l-4 border-blue-100 pl-4 py-1">
            <p className="text-[10px] text-slate-500 font-medium line-clamp-3 italic leading-relaxed">
              "{payload.Descrição}"
            </p>
          </div>
        )}
      </div>

      <div className="p-6 pt-0">
        <a
          href={payload["Link de acesso"]}
          target="_blank"
          rel="noopener noreferrer"
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-black py-4 rounded-2xl text-[11px] transition-all flex items-center justify-center gap-3 uppercase tracking-[0.2em] shadow-lg shadow-blue-200 group/btn"
        >
          Ver Documentação{" "}
          <ExternalLink className="w-4 h-4 transition-transform group-hover/btn:translate-x-1" />
        </a>
      </div>
    </motion.div>
  );
};

export default function App() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [filteredStats, setFilteredStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [fUf, setFUf] = useState("");
  const [fCity, setFCity] = useState("");
  const [fNeighborhood, setFNeighborhood] = useState("");
  const [fModalidade, setFModalidade] = useState("");
  const [fSort, setFSort] = useState("price_asc");

  const [optUfs, setOptUfs] = useState<any[]>([]);
  const [optCities, setOptCities] = useState<any[]>([]);
  const [optNeighborhoods, setOptNeighborhoods] = useState<any[]>([]);
  const [optModalidades, setOptModalidades] = useState<any[]>([]);
  const [loadingFilters, setLoadingFilters] = useState(false);

  useEffect(() => {
    const fetchBaseFilters = async () => {
      try {
        const res = await axios.get(
          `${API_BASE}/filters?uf=${fUf}&city=${fCity}&neighborhood=${fNeighborhood}&modalidade=${fModalidade}`,
        );
        if (res.data) {
          setOptUfs(res.data.ufs || []);
          setOptModalidades(res.data.modalidades || []);
        }
      } catch (e) {
        console.error("Erro ao atualizar filtros base:", e);
      }
    };
    fetchBaseFilters();
  }, [fUf, fCity, fNeighborhood, fModalidade]);

  // Reset hierárquico: Limpa filhos apenas se o pai geográfico mudar
  useEffect(() => {
    setFCity("");
    setFNeighborhood("");
    setFModalidade("");
  }, [fUf]);

  useEffect(() => {
    setFNeighborhood("");
  }, [fCity]);

  useEffect(() => {
    const fetchCities = async () => {
      if (!fUf) {
        setOptCities([]);
        return;
      }
      setLoadingFilters(true);
      try {
        const res = await axios.get(
          `${API_BASE}/filters?uf=${fUf}&modalidade=${fModalidade}`,
        );
        setOptCities(res.data.cities || []);
      } catch (e) {
      } finally {
        setLoadingFilters(false);
      }
    };
    fetchCities();
  }, [fUf, fModalidade]);

  useEffect(() => {
    const fetchNeighborhoods = async () => {
      if (!fCity) {
        setOptNeighborhoods([]);
        return;
      }
      setLoadingFilters(true);
      try {
        const res = await axios.get(
          `${API_BASE}/filters?uf=${fUf}&city=${fCity}&modalidade=${fModalidade}`,
        );
        setOptNeighborhoods(res.data.neighborhoods || []);
      } catch (e) {
      } finally {
        setLoadingFilters(false);
      }
    };
    fetchNeighborhoods();
  }, [fCity, fModalidade]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const urlParams = `?uf=${fUf}&city=${fCity}&neighborhood=${fNeighborhood}&modalidade=${fModalidade}`;
        const [pRes, sRes, fsRes] = await Promise.all([
          axios.get(
            `${API_BASE}/properties${urlParams}&limit=32&sort=${fSort}`,
          ),
          axios.get(`${API_BASE}/stats`),
          axios.get(`${API_BASE}/stats/filtered${urlParams}`),
        ]);
        setProperties(pRes.data || []);
        setStats(sRes.data || null);
        setFilteredStats(fsRes.data || null);
      } catch (err) {
        setError("Erro na conexão com o servidor 3001.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [fUf, fCity, fNeighborhood, fModalidade, fSort]);

  const resetFilters = () => {
    setFUf("");
    setFCity("");
    setFNeighborhood("");
    setFModalidade("");
    setFSort("price_asc");
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 overflow-x-hidden">
      <div className="max-w-7xl mx-auto px-6 py-12 space-y-12">
        <header className="flex flex-col md:flex-row justify-between items-center gap-6 border-b border-slate-200 pb-10">
          <div className="flex items-center gap-4 text-center md:text-left">
            <div className="w-14 h-14 bg-blue-600 rounded-2xl flex items-center justify-center shadow-xl shadow-blue-200">
              <Home className="text-white w-7 h-7" />
            </div>
            <div>
              <h1 className="text-3xl font-black text-slate-900 tracking-tight flex items-center gap-2">
                LEILÃO <span className="text-blue-600">INSIGHTS</span>
              </h1>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                Painel de Inteligência Imobiliária
              </p>
            </div>
          </div>

          {stats && (
            <div className="grid grid-cols-2 lg:flex items-center gap-6 lg:gap-8 bg-white px-6 lg:px-8 py-4 rounded-3xl shadow-sm border border-slate-100 w-full lg:w-auto">
              <div className="text-center">
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-tighter mb-1">
                  Imóveis Na Base
                </p>
                <p className="text-lg lg:text-xl font-black text-slate-900">
                  {stats.total?.toLocaleString()}
                </p>
              </div>
              <div className="hidden lg:block w-px h-8 bg-slate-100" />
              <div className="text-center">
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-tighter mb-1">
                  Cidades Cobertas
                </p>
                <p className="text-lg lg:text-xl font-black text-slate-900">
                  {stats.cities?.toLocaleString()}
                </p>
              </div>
              {filteredStats && filteredStats.average > 0 && (
                <>
                  <div className="hidden lg:block w-px h-8 bg-slate-100" />
                  <div className="text-center col-span-2 lg:col-span-1 border-t lg:border-t-0 pt-4 lg:pt-0">
                    <p className="text-[9px] font-black text-blue-600 uppercase tracking-tighter mb-1">
                      Média de Avaliação
                    </p>
                    <p className="text-lg lg:text-xl font-black text-slate-900">
                      R${" "}
                      {filteredStats.average.toLocaleString("pt-BR", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </p>
                  </div>
                  {filteredStats.median > 0 && (
                    <>
                      <div className="hidden lg:block w-px h-8 bg-slate-100" />
                      <div className="text-center col-span-2 lg:col-span-1 border-t lg:border-t-0 pt-4 lg:pt-0">
                        <p className="text-[9px] font-black text-emerald-600 uppercase tracking-tighter mb-1">
                          Mediana
                        </p>
                        <p className="text-lg lg:text-xl font-black text-slate-900">
                          R${" "}
                          {filteredStats.median.toLocaleString("pt-BR", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}
                        </p>
                      </div>
                    </>
                  )}
                </>
              )}
            </div>
          )}
        </header>

        <section className="bg-white p-8 rounded-[2.5rem] shadow-sm border border-slate-100 space-y-6">
          <div className="flex items-center justify-between px-2">
            <h3 className="text-[11px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
              <Filter className="w-4 h-4 text-blue-600" /> Refinar Busca
            </h3>
            <div className="flex items-center gap-3">
              <button
                onClick={() =>
                  setFSort((prev) =>
                    prev === "price_asc" ? "price_desc" : "price_asc",
                  )
                }
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-[10px] font-black transition-all ${
                  fSort === "price_asc"
                    ? "bg-blue-50 text-blue-600 border border-blue-100"
                    : "bg-slate-900 text-white shadow-lg shadow-slate-200"
                }`}
                title={
                  fSort === "price_asc"
                    ? "Ordenando por Menor Preço"
                    : "Ordenando por Maior Preço"
                }
              >
                <ArrowUpDown
                  className={`w-3.5 h-3.5 transition-transform duration-500 ${fSort === "price_desc" ? "rotate-180" : ""}`}
                />
                {fSort === "price_asc" ? "MENOR PREÇO" : "MAIOR PREÇO"}
              </button>

              {(fUf || fModalidade || fCity || fNeighborhood) && (
                <button
                  onClick={resetFilters}
                  className="text-[10px] font-black text-red-500 hover:text-red-600 flex items-center gap-2 transition-colors ml-2"
                  title="Limpar todos os filtros"
                >
                  <X className="w-3.5 h-3.5" /> LIMPAR
                </button>
              )}
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <MultiFilterSelect
              label="Estado"
              value={fUf}
              options={optUfs}
              onChange={setFUf}
              icon={Globe}
              isMulti={false}
            />
            <MultiFilterSelect
              label="Cidade"
              value={fCity}
              options={optCities}
              onChange={setFCity}
              icon={MapPin}
              disabled={!fUf}
              loading={loadingFilters}
              isMulti={true}
            />
            <MultiFilterSelect
              label="Bairro"
              value={fNeighborhood}
              options={optNeighborhoods}
              onChange={setFNeighborhood}
              icon={MapPin}
              disabled={!fCity}
              loading={loadingFilters}
              isMulti={true}
            />
            <MultiFilterSelect
              label="Modalidade"
              value={fModalidade}
              options={optModalidades}
              onChange={setFModalidade}
              icon={Tag}
              isMulti={true}
            />
          </div>
        </section>

        <main className="space-y-8">
          {error && (
            <div className="bg-red-50 border border-red-100 p-10 rounded-[3rem] text-center space-y-4">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-8 h-8 text-red-600" />
              </div>
              <h4 className="text-slate-900 font-black uppercase text-base">
                Ops! Algo deu errado.
              </h4>
              <p className="text-slate-500 text-sm max-w-md mx-auto">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="bg-slate-900 text-white px-8 py-3 rounded-2xl text-[11px] font-black uppercase tracking-widest shadow-lg hover:bg-slate-800 transition-all"
              >
                Tentar Novamente
              </button>
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center py-32 space-y-6">
              <div className="relative">
                <div className="w-12 h-12 border-4 border-blue-100 rounded-full animate-spin"></div>
                <div className="w-12 h-12 border-4 border-blue-600 rounded-full animate-spin absolute top-0 left-0 border-t-transparent"></div>
              </div>
              <p className="text-slate-400 text-[10px] font-black uppercase tracking-[0.3em] animate-pulse">
                Sincronizando com PostgreSQL...
              </p>
            </div>
          ) : (
            <AnimatePresence mode="popLayout">
              {properties.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10">
                  {properties.map((p) => (
                    <PropertyCard key={p.numero_imovel + p.uf} property={p} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-32 bg-white rounded-[4rem] border border-slate-100 shadow-sm">
                  <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-6">
                    <Search className="w-10 h-10 text-slate-200" />
                  </div>
                  <h3 className="text-slate-900 font-black text-xl uppercase mb-2">
                    Sem resultados
                  </h3>
                  <p className="text-slate-400 font-bold uppercase text-[10px] tracking-widest">
                    Tente ajustar seus filtros para encontrar novos imóveis
                  </p>
                </div>
              )}
            </AnimatePresence>
          )}
        </main>
      </div>
    </div>
  );
}
