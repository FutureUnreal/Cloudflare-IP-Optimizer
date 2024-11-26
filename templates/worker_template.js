// IP池配置 - 更新时间: {{UPDATE_TIME}}
const IP_POOLS = {{IP_POOLS}};

// 优选策略配置
const SELECTION_STRATEGY = {
    TIER_1: {
        priority: 1,
        strategy: 'ISP_MATCH',
        timeout: 1000,
        retries: 2
    },
    TIER_2: {
        priority: 2,
        strategy: 'SAME_ISP_DIFFERENT_REGION',
        timeout: 1500,
        retries: 2
    },
    TIER_3: {
        priority: 3,
        strategy: 'DIFFERENT_ISP_SAME_REGION',
        timeout: 2000,
        retries: 1
    }
};

// ASN到运营商的映射
const ASN_TO_ISP = {
    // 电信
    '4134': 'CHINA_TELECOM',
    '4809': 'CHINA_TELECOM',
    // 联通
    '4837': 'CHINA_UNICOM',
    '9929': 'CHINA_UNICOM',
    '4808': 'CHINA_UNICOM',
    // 移动
    '9808': 'CHINA_MOBILE',
    '56040': 'CHINA_MOBILE'
};

// 省份/地区到区域的映射
const REGION_MAPPING = {
    // 华东地区
    'Shanghai': 'EAST',
    'Jiangsu': 'EAST',
    'Zhejiang': 'EAST',
    'Anhui': 'EAST',
    'Fujian': 'EAST',
    'Jiangxi': 'EAST',
    'Shandong': 'EAST',

    // 华北地区
    'Beijing': 'NORTH',
    'Tianjin': 'NORTH',
    'Hebei': 'NORTH',
    'Shanxi': 'NORTH',
    'Inner Mongolia': 'NORTH',

    // 华南地区
    'Guangdong': 'SOUTH',
    'Guangxi': 'SOUTH',
    'Hainan': 'SOUTH',

    // 华中地区
    'Henan': 'CENTRAL',
    'Hubei': 'CENTRAL',
    'Hunan': 'CENTRAL',

    // 西南地区
    'Chongqing': 'SOUTHWEST',
    'Sichuan': 'SOUTHWEST',
    'Guizhou': 'SOUTHWEST',
    'Yunnan': 'SOUTHWEST',
    'Tibet': 'SOUTHWEST',

    // 西北地区
    'Shaanxi': 'NORTHWEST',
    'Gansu': 'NORTHWEST',
    'Qinghai': 'NORTHWEST',
    'Ningxia': 'NORTHWEST',
    'Xinjiang': 'NORTHWEST',

    // 东北地区
    'Liaoning': 'NORTHEAST',
    'Jilin': 'NORTHEAST',
    'Heilongjiang': 'NORTHEAST'
};

// Cloudflare区域代码映射
const CF_REGION_CODES = {
    // 华东地区
    'SHA': 'EAST',  // 上海
    'JSU': 'EAST',  // 江苏
    'ZHE': 'EAST',  // 浙江
    'ANH': 'EAST',  // 安徽
    'FUJ': 'EAST',  // 福建
    'JXI': 'EAST',  // 江西
    'SHD': 'EAST',  // 山东

    // 华北地区
    'BEJ': 'NORTH', // 北京
    'TAJ': 'NORTH', // 天津
    'HEB': 'NORTH', // 河北
    'SHX': 'NORTH', // 山西
    'NMG': 'NORTH', // 内蒙古

    // 华南地区
    'GUD': 'SOUTH', // 广东
    'GXI': 'SOUTH', // 广西
    'HAI': 'SOUTH', // 海南

    // 华中地区
    'HEN': 'CENTRAL', // 河南
    'HUB': 'CENTRAL', // 湖北
    'HUN': 'CENTRAL', // 湖南

    // 西南地区
    'CQG': 'SOUTHWEST', // 重庆
    'SCH': 'SOUTHWEST', // 四川
    'GZH': 'SOUTHWEST', // 贵州
    'YUN': 'SOUTHWEST', // 云南
    'TIB': 'SOUTHWEST', // 西藏

    // 西北地区
    'SHN': 'NORTHWEST', // 陕西
    'GAN': 'NORTHWEST', // 甘肃
    'QIN': 'NORTHWEST', // 青海
    'NXA': 'NORTHWEST', // 宁夏
    'XIN': 'NORTHWEST', // 新疆

    // 东北地区
    'LIA': 'NORTHEAST', // 辽宁
    'JIL': 'NORTHEAST', // 吉林
    'HLJ': 'NORTHEAST'  // 黑龙江
};

addEventListener('fetch', event => {
    event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
    const clientInfo = {
        ip: request.headers.get('CF-Connecting-IP'),
        asn: request.cf.asn,
        region: request.cf.region,
        city: request.cf.city,
        country: request.cf.country,
        latitude: request.cf.latitude,
        longitude: request.cf.longitude
    };

    try {
        const isp = determineISP(clientInfo.asn);
        const region = determineRegion(clientInfo);
        const bestIP = await selectBestIP(isp, region);

        return new Response(JSON.stringify({
            status: 'success',
            client: {
                ip: clientInfo.ip,
                isp,
                region,
                city: clientInfo.city,
                asn: clientInfo.asn
            },
            optimized_ip: bestIP,
            ttl: 300,
            timestamp: Date.now()
        }), {
            headers: {
                'content-type': 'application/json',
                'cache-control': 'max-age=300'
            }
        });
    } catch (error) {
        return new Response(JSON.stringify({
            status: 'error',
            message: error.message
        }), {
            status: 500,
            headers: { 'content-type': 'application/json' }
        });
    }
}

function determineISP(asn) {
    return ASN_TO_ISP[asn] || 'UNKNOWN';
}

function determineRegionByCoordinates(lat, lon) {
    // 经纬度范围定义
    const regions = {
        NORTHEAST: { minLat: 40, maxLat: 55, minLon: 120, maxLon: 135 },
        NORTH: { minLat: 35, maxLat: 43, minLon: 110, maxLon: 120 },
        NORTHWEST: { minLat: 35, maxLat: 45, minLon: 75, maxLon: 110 },
        EAST: { minLat: 25, maxLat: 35, minLon: 115, maxLon: 123 },
        CENTRAL: { minLat: 25, maxLat: 35, minLon: 108, maxLon: 115 },
        SOUTHWEST: { minLat: 20, maxLat: 35, minLon: 97, maxLon: 108 },
        SOUTH: { minLat: 18, maxLat: 25, minLon: 105, maxLon: 120 }
    };

    for (const [region, bounds] of Object.entries(regions)) {
        if (lat >= bounds.minLat && lat <= bounds.maxLat && 
            lon >= bounds.minLon && lon <= bounds.maxLon) {
            return region;
        }
    }

    return 'EAST';  // 默认返回华东地区
}

function determineRegion(clientInfo) {
    // 1. 优先使用Cloudflare的region code
    if (clientInfo.region && CF_REGION_CODES[clientInfo.region]) {
        return CF_REGION_CODES[clientInfo.region];
    }

    // 2. 尝试使用城市名称匹配
    if (clientInfo.city && REGION_MAPPING[clientInfo.city]) {
        return REGION_MAPPING[clientInfo.city];
    }

    // 3. 使用经纬度判断
    if (clientInfo.latitude && clientInfo.longitude) {
        return determineRegionByCoordinates(clientInfo.latitude, clientInfo.longitude);
    }

    return 'EAST';  // 默认返回华东地区
}

async function selectBestIP(isp, region) {
    // 按策略选择最佳IP
    for (const tier of Object.values(SELECTION_STRATEGY)) {
        const ip = await trySelectIP(isp, region, tier);
        if (ip) return ip;
    }
    throw new Error('No available IP');
}

async function trySelectIP(isp, region, tier) {
    try {
        let candidateIPs = [];
        
        switch (tier.strategy) {
            case 'ISP_MATCH':
                // 同运营商同地区
                candidateIPs = IP_POOLS[isp]?.[region] || [];
                break;
                
            case 'SAME_ISP_DIFFERENT_REGION':
                // 同运营商跨地区
                candidateIPs = Object.values(IP_POOLS[isp] || {})
                    .flat()
                    .filter(ip => !IP_POOLS[isp]?.[region]?.includes(ip));
                break;
                
            case 'DIFFERENT_ISP_SAME_REGION':
                // 跨运营商同地区
                for (const otherISP of Object.keys(IP_POOLS)) {
                    if (otherISP !== isp) {
                        candidateIPs.push(...(IP_POOLS[otherISP]?.[region] || []));
                    }
                }
                break;
        }

        // 测试候选IP
        for (const ip of candidateIPs) {
            for (let i = 0; i < tier.retries; i++) {
                try {
                    const response = await fetch(`http://${ip}/cdn-cgi/trace`, {
                        cf: { timeout: tier.timeout }
                    });
                    if (response.ok) {
                        return ip;
                    }
                } catch (error) {
                    continue;
                }
            }
        }

        return null;
    } catch (error) {
        console.error('IP selection error:', error);
        return null;
    }
}