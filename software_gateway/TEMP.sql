SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";


CREATE TABLE `TEMP` (
  `sequence` int(11) NOT NULL COMMENT 'PK',
  `mac` char(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'mac address',
  `station` char(50) COLLATE utf8mb4_unicode_ci DEFAULT '0' COMMENT '位置',
  `id` int(11) NOT NULL DEFAULT '0' COMMENT 'CARD ID',
  `name` char(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '名字',
  `number` char(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '學號工號',
  `temperature` double NOT NULL DEFAULT '0' COMMENT '體溫',
  `updatetime` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '上傳時間'
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


ALTER TABLE `TEMP`
  ADD PRIMARY KEY (`sequence`);


ALTER TABLE `TEMP`
  MODIFY `sequence` int(11) NOT NULL AUTO_INCREMENT COMMENT 'PK', AUTO_INCREMENT=1;
COMMIT;
