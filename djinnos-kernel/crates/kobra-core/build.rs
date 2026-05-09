// Generates sorted_symbols.rs: all 1358 Shygazun symbols sorted by name
// length descending (required for greedy longest-prefix matching in the
// sublayer).  Runs on the host at build time; no no_std constraints.

use std::io::Write;

fn main() {
    let raw: &[(&str, u16)] = &[
        // Lotus (0-23)
        ("Ty",0),("Zu",1),("Ly",2),("Mu",3),("Fy",4),("Pu",5),("Shy",6),
        ("Ku",7),("Ti",8),("Ta",9),("Li",10),("La",11),("Fi",12),("Fa",13),
        ("Shi",14),("Sha",15),("Zo",16),("Mo",17),("Po",18),("Ko",19),
        ("Ze",20),("Me",21),("Pe",22),("Ke",23),
        // Rose (24-47)
        ("Ru",24),("Ot",25),("El",26),("Ki",27),("Fu",28),("Ka",29),
        ("AE",30),("Gaoh",31),("Ao",32),("Ye",33),("Ui",34),("Shu",35),
        ("Kiel",36),("Yeshu",37),("Lao",38),("Shushy",39),("Uinshu",40),
        ("Kokiel",41),("Aonkiel",42),("Ha",43),("Ga",44),("Wu",45),
        ("Na",46),("Ung",47),
        // Sakura (48-71)
        ("Jy",48),("Ji",49),("Ja",50),("Jo",51),("Je",52),("Ju",53),
        ("Dy",54),("Di",55),("Da",56),("Do",57),("De",58),("Du",59),
        ("By",60),("Bi",61),("Ba",62),("Bo",63),("Be",64),("Bu",65),
        ("Va",66),("Vo",67),("Ve",68),("Vu",69),("Vi",70),("Vy",71),
        // Daisy (72-97)
        ("Lo",72),("Yei",73),("Ol",74),("X",75),("Yx",76),("Go",77),
        ("Foa",78),("Oy",79),("W",80),("Th",81),("Kael",82),("Ro",83),
        ("Gl",84),("To",85),("Ma",86),("Ne",87),("Ym",88),("Nz",89),
        ("Sho",90),("Hi",91),("Mh",92),("Zhi",93),("Vr",94),("St",95),
        ("Fn",96),("N",97),
        // AppleBlossom (98-123)
        ("A",98),("O",99),("I",100),("E",101),("Y",102),("U",103),
        ("Shak",104),("Puf",105),("Mel",106),("Zot",107),("Zhuk",108),
        ("Kypa",109),("Alky",110),("Kazho",111),("Puky",112),("Pyfu",113),
        ("Mipa",114),("Zitef",115),("Shem",116),("Lefu",117),("Milo",118),
        ("Myza",119),("Zashu",120),("Fozt",121),("Mazi",122),("Zaot",123),
        // Reserved (124-127)
        ("YeGaoh-Index",124),("YeGaoh-1-8",125),("YeGaoh-9-16",126),("YeGaoh-17-24",127),
        // Aster (128-155)
        ("Ry",128),("Oth",129),("Le",130),("Gi",131),("Fe",132),("Ky",133),
        ("Alz",134),("Ra",135),("Tho",136),("Lu",137),("Ge",138),("Fo",139),
        ("Kw",140),("Dr",141),("Si",142),("Su",143),("Os",144),("Se",145),
        ("Sy",146),("As",147),("Ep",148),("Gwev",149),("Ifa",150),("Ier",151),
        ("San",152),("Enno",153),("Yl",154),("Hoz",155),
        // Grapevine (156-183)
        ("Sa",156),("Sao",157),("Syr",158),("Seth",159),("Samos",160),
        ("Sava",161),("Sael",162),("Myk",163),("Myr",164),("Mio",165),
        ("Mek",166),("Mavo",167),("Mekha",168),("Myrun",169),("Dyf",170),
        ("Dyo",171),("Dyth",172),("Dyska",173),("Dyne",174),("Dyran",175),
        ("Dyso",176),("Kyf",177),("Kyl",178),("Kyra",179),("Kyvos",180),
        ("Kysha",181),("Kyom",182),("Kysael",183),
        // Cannabis (184-213)
        ("At",184),("Ar",185),("Av",186),("Azr",187),("Af",188),("An",189),
        ("Od",190),("Ox",191),("Om",192),("Soa",193),("It",194),("Ir",195),
        ("Iv",196),("Izr",197),("If",198),("In",199),("Ed",200),("Ex",201),
        ("Em",202),("Sei",203),("Yt",204),("Yr",205),("Yv",206),("Yzr",207),
        ("Yf",208),("Yn",209),("Ud",210),("Ux",211),("Um",212),("Suy",213),
        // Reserved/Meta (214-227)
        ("YeYe-Index",214),("YeYe-1-13",215),("YeYe-14-26",216),
        ("YeShu-Index",217),("YeShu-1-7",218),("YeShu-8-14",219),
        ("YeShu-15-21",220),("YeShu-22-28",221),("YeYeshu-Index",222),
        ("YeYeshu-1-6",223),("YeYeshu-7-12",224),("YeYeshu-13-18",225),
        ("YeYeshu-19-24",226),("YeYeshu-25-30",227),
        // Dragon (256-285)
        ("Rhivesh",256),("Rhokve",257),("Rhezh",258),("Rhivash-ko",259),
        ("Zhri'val",260),("Rhasha-vok",261),("Vzhiran",262),("Rhokvesh-na",263),
        ("Vzhiral-rhe",264),("Rhazhvu-nokte",265),("Dvavesh",266),("Dvokran",267),
        ("Dva'zhal",268),("Dvasha-ke",269),("Zhrdva-vol",270),("Dvokesh",271),
        ("Vzhrdva",272),("Dvokrash-na",273),("Rhdva-vun",274),("Dvazh-nokvre",275),
        ("Kwevesh",276),("Kwokre",277),("Kwe'zhal",278),("Kwasha-val",279),
        ("Zhrkwe-na",280),("Kwokvesh",281),("Vzhrkwe",282),("Kwokrash-rhe",283),
        ("Rhkwe-vun",284),("Kwazhvu-nokte",285),
        // Virus (286-315)
        ("Plave",286),("Plaro",287),("Plahan",288),("Plaung",289),("Plaha",290),
        ("Plana",291),("Plawu",292),("Plaoku",293),("Plavik",294),("Plavikro",295),
        ("Jruve",296),("Jrushan",297),("Jrulok",298),("Jruval",299),("Jru'wun",300),
        ("Jruvekna",301),("Jrukash",302),("Jruvashko",303),("Jrukashro",304),
        ("Jrunokvre",305),("Wikve",306),("Wikro",307),("Wikhan",308),("Wikval",309),
        ("Wikvalna",310),("Wikung",311),("Wikaro",312),("Wiknasha",313),
        ("Wikshavel",314),("Wiknokvre",315),
        // Bacteria (316-345)
        ("Zhove",316),("Zhoran",317),("Zhokre",318),("Zho'val",319),("Zho'na",320),
        ("Zhovesh",321),("Zhuvek",322),("Zhokrash",323),("Zhokven",324),
        ("Zhokven-na",325),("Rive",326),("Rivan",327),("Riko",328),("Rival",329),
        ("Ri'vash",330),("Rikash",331),("Rikove",332),("Rizhun",333),("Rivekna",334),
        ("Rikrasho",335),("Vavre",336),("Varan",337),("Varko",338),("Varval",339),
        ("Var'zho",340),("Varlok",341),("Varshan",342),("Varkash",343),
        ("Varnokre",344),("Varzhokrash",345),
        // Excavata (346-377)
        ("Ranve",346),("Ranvu",347),("Ranpek",348),("Ranval",349),("Ran'vo",350),
        ("Rankwe",351),("Ranvesh",352),("Rankovre",353),("Ranzhok",354),
        ("Rankrash-vo",355),("Yefve",356),("Yefran",357),("Yeflo",358),
        ("Yefval",359),("Yef'na",360),("Yefkash",361),("Yefkovre",362),
        ("Yefvash-lo",363),("Yefranog",364),("Yefzhokran",365),("Logve",366),
        ("Logan",367),("Logran",368),("Logval",369),("Log'vesh",370),
        ("Logkash",371),("Logkre",372),("Logzhok",373),("Logvekna",374),
        ("Logranzhok",375),("Yefko",376),("Ranku",377),
        // Archaeplastida (378-409)
        ("Zotve",378),("Zotan",379),("Zotkre",380),("Zot'vel",381),
        ("Zotvash",382),("Zotzhok",383),("Zotkash-ran",384),("Zotnavre",385),
        ("Melve",386),("Melan",387),("Melko",388),("Mel'vash",389),
        ("Melpik",390),("Melvek",391),("Melkash",392),("Melzotkre",393),
        ("Pufve",394),("Pufan",395),("Pufko",396),("Puf'val",397),
        ("Pufzot",398),("Pufkash",399),("Pufranve",400),("Pufshakna",401),
        ("Shakve",402),("Shakran",403),("Shakvesh",404),("Shak'mel",405),
        ("Shakpuf",406),("Shakazh",407),("Shakvekna",408),("Shakzotmel",409),
        // Myxozoa (410-443)
        ("Ive",410),("Ivi",411),("Ivu",412),("Ivo",413),("Iva",414),("Ivoe",415),
        ("Oave",416),("Oavi",417),("Oavu",418),("Oavo",419),("Oava",420),("Oavoe",421),
        ("Navsh",422),("Navp",423),("Navm",424),("Navz",425),("Navk",426),
        ("Ivelo",427),("Ivilo",428),("Ivulo",429),("Ivolo",430),("Ivalo",431),
        ("Ivoelo",432),("Oavelo",433),("Oavilo",434),("Oavulo",435),("Oavolo",436),
        ("Oavalo",437),("Oavoelo",438),("Navshlo",439),("Navplo",440),
        ("Navmlo",441),("Navzlo",442),("Navklo",443),
        // Archaea (444-477)
        ("Ethe",444),("Ethi",445),("Ethu",446),("Etho",447),("Etha",448),("Ethoe",449),
        ("Urge",450),("Urgi",451),("Urgu",452),("Urgo",453),("Urga",454),("Urgoe",455),
        ("Krevsh",456),("Krevp",457),("Krevm",458),("Krevz",459),("Krevk",460),
        ("Ethelo",461),("Ethilo",462),("Ethulo",463),("Etholo",464),("Ethalo",465),
        ("Ethoelo",466),("Urgelo",467),("Urgilo",468),("Urgulo",469),("Urgolo",470),
        ("Urgalo",471),("Urgoelo",472),("Krevshlo",473),("Krevplo",474),
        ("Krevmlo",475),("Krevzlo",476),("Krevklo",477),
        // Protist (478-511)
        ("Aeve",478),("Aevi",479),("Aevu",480),("Aevo",481),("Aeva",482),("Aevoe",483),
        ("Oive",484),("Oivi",485),("Oivu",486),("Oivo",487),("Oiva",488),("Oivoe",489),
        ("Grevsh",490),("Grevp",491),("Grevm",492),("Grevz",493),("Grevk",494),
        ("Aevelo",495),("Aevilo",496),("Aevulo",497),("Aevolo",498),("Aevalo",499),
        ("Aevoelo",500),("Oivelo",501),("Oivilo",502),("Oivulo",503),("Oivolo",504),
        ("Oivalo",505),("Oivoelo",506),("Grevshlo",507),("Grevplo",508),
        ("Grevmlo",509),("Grevzlo",510),("Grevklo",511),
        // Immune (512-545)
        ("Sive",512),("Sivi",513),("Sivu",514),("Sivo",515),("Siva",516),("Sivoe",517),
        ("Reke",518),("Reki",519),("Reku",520),("Reko",521),("Reka",522),("Rekoe",523),
        ("Trevsh",524),("Trevp",525),("Trevm",526),("Trevz",527),("Trevk",528),
        ("Sivelo",529),("Sivilo",530),("Sivulo",531),("Sivolo",532),("Sivalo",533),
        ("Sivoelo",534),("Rekelo",535),("Rekilo",536),("Rekulo",537),("Rekolo",538),
        ("Rekalo",539),("Rekoelo",540),("Trevshlo",541),("Trevplo",542),
        ("Trevmlo",543),("Trevzlo",544),("Trevklo",545),
        // Neural (546-581)
        ("Vele",546),("Veli",547),("Velu",548),("Velo",549),("Vela",550),("Veloe",551),
        ("Nale",552),("Nali",553),("Nalu",554),("Nalo",555),("Nala",556),("Naloe",557),
        ("Dreve",558),("Drevi",559),("Drevu",560),("Drevo",561),("Dreva",562),("Drevoe",563),
        ("Velelo",564),("Velilo",565),("Velulo",566),("Velolo",567),("Velalo",568),
        ("Veloelo",569),("Nalelo",570),("Nalilo",571),("Nalulo",572),("Nalolo",573),
        ("Nalalo",574),("Naloelo",575),("Drevelo",576),("Drevilo",577),("Drevulo",578),
        ("Drevolo",579),("Drevalo",580),("Drevoelo",581),
        // Serpent (582-617)
        ("Mash",582),("Mosh",583),("Mish",584),("Mesh",585),("Mysh",586),("Mush",587),
        ("Kal",588),("Kol",589),("Kil",590),("Kel",591),("Kyl",592),("Kul",593),
        ("Zaf",594),("Zof",595),("Zif",596),("Zef",597),("Zyf",598),("Zuf",599),
        ("Pat",600),("Pot",601),("Pit",602),("Pet",603),("Pyt",604),("Put",605),
        ("Maf",606),("Mof",607),("Mif",608),("Mef",609),("Myf",610),("Muf",611),
        ("Kat",612),("Kot",613),("Kit",614),("Ket",615),("Kyt",616),("Kut",617),
        // Beast (618-655)
        ("Geve",618),("Gevi",619),("Gevu",620),("Gevo",621),("Geva",622),("Gevoe",623),
        ("Prale",624),("Prali",625),("Pralu",626),("Pralo",627),("Prala",628),("Praloe",629),
        ("Dreke",630),("Dreki",631),("Dreku",632),("Dreko",633),("Dreka",634),("Drekoe",635),
        ("Gevelo",636),("Gevilo",637),("Gevulo",638),("Gevolo",639),("Gevalo",640),
        ("Gevoelo",641),("Pralelo",642),("Pralilo",643),("Pralulo",644),("Pralolo",645),
        ("Pralalo",646),("Praloelo",647),("Drekelo",648),("Drekilo",649),("Drekulo",650),
        ("Drekolo",651),("Drekalo",652),("Drekoelo",653),("Grevvi",654),("Grevvo",655),
        // Cherub (656-693)
        ("Sheve",656),("Shevi",657),("Shevu",658),("Shevo",659),("Sheva",660),("Shevoe",661),
        ("Threle",662),("Threli",663),("Threlu",664),("Threlo",665),("Threla",666),("Threloe",667),
        ("Vlove",668),("Vlovi",669),("Vlovu",670),("Vlovo",671),("Vlova",672),("Vlovoe",673),
        ("Shevelo",674),("Shevilo",675),("Shevulo",676),("Shevolo",677),("Shevalo",678),
        ("Shevoelo",679),("Threlelo",680),("Threlilo",681),("Threlulo",682),("Threlolo",683),
        ("Threlalo",684),("Threloelo",685),("Vlovelo",686),("Vlovilo",687),("Vlovulo",688),
        ("Vlovolo",689),("Vlovalo",690),("Vlovoelo",691),("Shrev",692),("Shrov",693),
        // Chimera (694-731)
        ("Glove",694),("Glovi",695),("Glovu",696),("Glovo",697),("Glova",698),("Glovoe",699),
        ("Preste",700),("Presti",701),("Prestu",702),("Presto",703),("Presta",704),("Prestoe",705),
        ("Wreke",706),("Wreki",707),("Wreku",708),("Wreko",709),("Wreka",710),("Wrekoe",711),
        ("Glovelo",712),("Glovilo",713),("Glovulo",714),("Glovolo",715),("Glovalo",716),
        ("Glovoelo",717),("Prestelo",718),("Prestilo",719),("Prestulo",720),("Prestolo",721),
        ("Prestalo",722),("Prestoelo",723),("Wrekelo",724),("Wrekilo",725),("Wrekulo",726),
        ("Wrekolo",727),("Wrekalo",728),("Wrekoelo",729),("Chrev",730),("Chrov",731),
        // Faerie (732-769)
        ("Feve",732),("Fevi",733),("Fevu",734),("Fevo",735),("Feva",736),("Fevoe",737),
        ("Zele",738),("Zeli",739),("Zelu",740),("Zelo",741),("Zela",742),("Zeloe",743),
        ("Plove",744),("Plovi",745),("Plovu",746),("Plovo",747),("Plova",748),("Plovoe",749),
        ("Fevelo",750),("Fevilo",751),("Fevulo",752),("Fevolo",753),("Fevalo",754),
        ("Fevoelo",755),("Zelelo",756),("Zelilo",757),("Zelulo",758),("Zelolo",759),
        ("Zelalo",760),("Zeloelo",761),("Plovelo",762),("Plovilo",763),("Plovulo",764),
        ("Plovolo",765),("Plovalo",766),("Plovoelo",767),("Farev",768),("Farov",769),
        // Djinn (770-809)
        ("Amsh",770),("Akl",771),("Azf",772),("Apt",773),("Amf",774),("Akt",775),
        ("Omsh",776),("Okl",777),("Ozf",778),("Opt",779),("Omf",780),("Okt",781),
        ("Imsh",782),("Ikl",783),("Izf",784),("Ipt",785),("Imf",786),("Ikt",787),
        ("Emsh",788),("Ekl",789),("Ezf",790),("Ept",791),("Emf",792),("Ekt",793),
        ("Ymsh",794),("Ykl",795),("Yzf",796),("Ypt",797),("Ymf",798),("Ykt",799),
        ("Umsh",800),("Ukl",801),("Uzf",802),("Upt",803),("Umf",804),("Ukt",805),
        ("Djrev",806),("Djrov",807),("Djruv",808),("Djriv",809),
        // Fold (810-849)
        ("Josje",810),("Josji",811),("Josja",812),("Josjo",813),("Josble",814),
        ("Josbli",815),("Josbla",816),("Josblo",817),("Josde",818),("Josdi",819),
        ("Josda",820),("Josdo",821),("Josve",822),("Josvi",823),("Josva",824),("Josvo",825),
        ("Blisle",826),("Blisli",827),("Blisla",828),("Blislo",829),("Blisde",830),
        ("Blisdi",831),("Blisda",832),("Blisdo",833),("Blisve",834),("Blisvi",835),
        ("Blisva",836),("Blisvo",837),("Dasde",838),("Dasdi",839),("Dasda",840),
        ("Dasdo",841),("Dasve",842),("Dasvi",843),("Dasva",844),("Dasvo",845),
        ("Vexe",846),("Vexi",847),("Vexa",848),("Vexo",849),
        // Topology (850-889) — using simplified names for hyphened compounds
        ("Toreve",850),("Torevi",851),("Torevu",852),("Torevo",853),("Torevy",854),
        ("Glaene",874),("Glaeni",875),("Glaenu",876),("Glaeno",877),("Glaeny",878),
        // Phase (890-929)
        ("Shavka",890),("Shavki",891),("Shavku",892),("Shavko",893),("Shavky",894),
        ("Blispa",896),("Blispi",897),("Blispu",898),("Blispo",899),
        ("Pufzota",902),("Pufzoti",903),("Pufzotu",904),("Pufzoto",905),
        ("Zotvex",908),("Zotvei",909),("Zotveu",910),("Zotveo",911),
        ("Kaelsha",914),("Kaelshi",915),("Kaelshu",916),("Kaelsho",917),
        ("Shaktika",920),("Shaktiki",921),("Shaktiku",922),("Shaktiko",923),
        // Gradient (930-969)
        ("Skathe",934),("Skathi",935),("Skatha",936),("Skatho",937),
        ("Phelve",938),("Phelvi",939),("Phelva",940),("Phelvo",941),
        ("Zolne",942),("Zolni",943),("Zolna",944),("Zolno",945),
        // Curvature (970-1009)
        ("Vreske",970),("Vreski",971),("Vreska",972),("Vresko",973),
        ("Tholve",974),("Tholvi",975),("Tholva",976),("Tholvo",977),
        ("Frenze",978),("Frenzi",979),("Frenza",980),("Frenzo",981),
        ("Glathne",982),("Glathni",983),("Glathna",984),("Glathno",985),
        // Prion (1010-1051)
        ("Ojnaje",1010),("Ojnaji",1011),("Ojnaja",1012),("Ojnajo",1013),
        ("Ojnake",1014),("Ojnaki",1015),("Ojnaka",1016),("Ojnako",1017),
        ("Ojnape",1018),("Ojnapi",1019),("Ojnapa",1020),("Ojnapo",1021),
        ("Icheke",1026),("Icheki",1027),("Icheka",1028),("Icheko",1029),
        ("Ichepe",1030),("Ichepi",1031),("Ichepa",1032),("Ichepo",1033),
        ("Upype",1038),("Upypi",1039),("Upypa",1040),("Upypo",1041),
        ("Vajya",1050),("Vajeu",1051),
        // Blood (1052-1093)
        ("Rua",1052),("Ruo",1053),("Rui",1054),("Rue",1055),("Ruy",1056),("Ruu",1057),
        ("Ota",1058),("Oto",1059),("Oti",1060),("Ote",1061),("Oty",1062),("Otu",1063),
        ("Ela",1064),("Elo",1065),("Eli",1066),("Ele",1067),("Ely",1068),("Elu",1069),
        ("Kia",1070),("Kio",1071),("Kii",1072),("Kie",1073),("Kiy",1074),("Kiu",1075),
        ("Fua",1076),("Fuo",1077),("Fui",1078),("Fue",1079),("Fuy",1080),("Fuu",1081),
        ("Kaa",1082),("Kao",1083),("Kai",1084),("Kae",1085),("Kay",1086),("Kau",1087),
        ("AEa",1088),("AEo",1089),("AEi",1090),("AEe",1091),("AEy",1092),("AEu",1093),
        // Moon (1094-1137)
        ("Akrazot",1094),("Ubnuzot",1095),("Idsizot",1096),("Athmazot",1097),
        ("Ownozot",1098),("Ymsyzot",1099),("Ejurzot",1100),("Abdozot",1101),
        ("Okvozot",1102),("Oharzot",1103),("Egzezot",1104),("Akramel",1105),
        ("Ubnumel",1106),("Idsimel",1107),("Athmamel",1108),("Ownomel",1109),
        ("Ymsymel",1110),("Ejurmel",1111),("Abdomel",1112),("Okvomel",1113),
        ("Oharmel",1114),("Egzemel",1115),("Akrapuf",1116),("Ubnupuf",1117),
        ("Idsipuf",1118),("Athmapuf",1119),("Ownopuf",1120),("Ymsypuf",1121),
        ("Ejurpuf",1122),("Abdopuf",1123),("Okvopuf",1124),("Oharpuf",1125),
        ("Egzepuf",1126),("Akrashak",1127),("Ubnushak",1128),("Idsishak",1129),
        ("Athmashak",1130),("Ownoshak",1131),("Ymsyshak",1132),("Ejurshak",1133),
        ("Abdoshak",1134),("Okvoshak",1135),("Oharshak",1136),("Egzeshak",1137),
        // Koi (1138-1181)
        ("Mav",1138),("Mov",1139),("Miv",1140),("Mev",1141),("Myv",1142),("Muv",1143),
        ("Grev",1144),("Kav",1148),("Kov",1149),("Kiv",1150),("Kev",1151),("Kyv",1152),("Kuv",1153),
        ("Grov",1154),("Frov",1157),("Zav",1158),("Zov",1159),("Ziv",1160),("Zev",1161),
        ("Zyv",1162),("Zuv",1163),("Gruv",1164),("Fruv",1167),("Pav",1168),("Pov",1169),
        ("Piv",1170),("Pev",1171),("Pyv",1172),("Puv",1173),("Griv",1174),("Friv",1177),
        ("Rev",1178),("Rov",1179),("Ruv",1180),("Riv",1181),
        // Rope (1182-1225)
        ("Mab",1182),("Mob",1183),("Mib",1184),("Meb",1185),("Myb",1186),("Mub",1187),
        ("Greb",1188),("Kab",1192),("Kob",1193),("Kib",1194),("Keb",1195),("Kyb",1196),("Kub",1197),
        ("Grob",1198),("Frob",1201),("Zab",1202),("Zob",1203),("Zib",1204),("Zeb",1205),
        ("Zyb",1206),("Zub",1207),("Grub",1208),("Frub",1211),("Pab",1212),("Pob",1213),
        ("Pib",1214),("Peb",1215),("Pyb",1216),("Pub",1217),("Grib",1218),("Frib",1221),
        ("Reb",1222),("Rob",1223),("Rub",1224),("Rib",1225),
        // Hook (1226-1269)
        ("Mag",1226),("Mog",1227),("Mig",1228),("Meg",1229),("Myg",1230),("Mug",1231),
        ("Greg",1232),("Kag",1236),("Kog",1237),("Kig",1238),("Keg",1239),("Kyg",1240),("Kug",1241),
        ("Grog",1242),("Frog",1245),("Zag",1246),("Zog",1247),("Zig",1248),("Zeg",1249),
        ("Zyg",1250),("Zug",1251),("Grug",1252),("Frug",1255),("Pag",1256),("Pog",1257),
        ("Pig",1258),("Peg",1259),("Pyg",1260),("Pug",1261),("Grig",1262),("Frig",1265),
        ("Reg",1266),("Rog",1267),("Rug",1268),("Rig",1269),
        // Fang (1270-1313)
        ("Madj",1270),("Modj",1271),("Midj",1272),("Medj",1273),("Mydj",1274),("Mudj",1275),
        ("Gredj",1276),("Kadj",1280),("Kodj",1281),("Kidj",1282),("Kedj",1283),("Kydj",1284),("Kudj",1285),
        ("Grodj",1286),("Frodj",1289),("Zadj",1290),("Zodj",1291),("Zidj",1292),("Zedj",1293),
        ("Zydj",1294),("Zudj",1295),("Grudj",1296),("Frudj",1299),("Padj",1300),("Podj",1301),
        ("Pidj",1302),("Pedj",1303),("Pydj",1304),("Pudj",1305),("Gridj",1306),("Fridj",1309),
        ("Redj",1310),("Rodj",1311),("Rudj",1312),("Ridj",1313),
        // Circle (1314-1357)
        ("Man",1314),("Mon",1315),("Min",1316),("Men",1317),("Myn",1318),("Mun",1319),
        ("Gren",1320),("Kan",1324),("Kon",1325),("Kin",1326),("Ken",1327),("Kyn",1328),("Kun",1329),
        ("Gron",1330),("Fron",1333),("Zan",1334),("Zon",1335),("Zin",1336),("Zen",1337),
        ("Zyn",1338),("Zun",1339),("Grun",1340),("Frun",1343),("Pan",1344),("Pon",1345),
        ("Pin",1346),("Pen",1347),("Pyn",1348),("Pun",1349),("Grin",1350),("Frin",1353),
        ("Ren",1354),("Ron",1355),("Run",1356),("Rin",1357),
    ];

    // Sort: longest name first, then alphabetically within same length.
    let mut sorted: Vec<(&str, u16)> = raw.to_vec();
    sorted.sort_by(|a, b| b.0.len().cmp(&a.0.len()).then(a.0.cmp(b.0)));

    let out_dir = std::env::var("OUT_DIR").unwrap();
    let path = format!("{}/sorted_symbols.rs", out_dir);
    let mut f = std::fs::File::create(&path).unwrap();

    writeln!(f, "/// All Shygazun symbols sorted longest-first for greedy prefix matching.").unwrap();
    writeln!(f, "pub const SYMBOLS: &[(&str, u16)] = &[").unwrap();
    for (name, addr) in &sorted {
        writeln!(f, "    ({:?}, {}),", name, addr).unwrap();
    }
    writeln!(f, "];").unwrap();

    println!("cargo:rerun-if-changed=build.rs");
}